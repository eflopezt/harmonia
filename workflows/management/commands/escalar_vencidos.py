"""
Management command: escalar_vencidos
=====================================
Finds all workflow instances (InstanciaFlujo) where the current stage
deadline (etapa_vence_en) has passed and estado = 'EN_PROCESO', then
applies escalation logic based on the stage's accion_vencimiento setting.

Usage:
    python manage.py escalar_vencidos
    python manage.py escalar_vencidos --dry-run
    python manage.py escalar_vencidos --verbosity 2

Schedule with Celery beat or a cron job to run every hour.
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Escala o procesa automaticamente los pasos de flujo vencidos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Muestra los flujos vencidos sin tomar accion',
        )

    def handle(self, *args, **options):
        from workflows.models import InstanciaFlujo, PasoFlujo

        ahora = timezone.now()
        dry_run = options['dry_run']
        verbosity = options['verbosity']

        vencidas = InstanciaFlujo.objects.filter(
            estado='EN_PROCESO',
            etapa_vence_en__lt=ahora,
            etapa_actual__isnull=False,
        ).select_related('etapa_actual', 'flujo', 'solicitante')

        total = vencidas.count()

        if verbosity >= 1:
            self.stdout.write(
                self.style.WARNING(
                    f'[escalar_vencidos] {total} instancia(s) vencida(s) encontrada(s) '
                    f'{"(dry-run)" if dry_run else ""}'
                )
            )

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Sin instancias vencidas. Todo al dia.'))
            return

        procesadas = escaladas = auto_aprobadas = auto_rechazadas = esperadas = 0

        for instancia in vencidas:
            etapa = instancia.etapa_actual
            accion = etapa.accion_vencimiento

            if verbosity >= 2:
                self.stdout.write(
                    f'  Instancia #{instancia.pk} | Flujo: {instancia.flujo.nombre} | '
                    f'Etapa: {etapa.nombre} | Accion: {accion} | '
                    f'Vencio: {instancia.etapa_vence_en}'
                )

            if accion == 'ESPERAR':
                # Just notify, no automatic action
                esperadas += 1
                if not dry_run:
                    self._notificar_vencimiento(instancia, etapa)
                if verbosity >= 2:
                    self.stdout.write(f'    -> ESPERAR: notificado sin tomar accion')
                continue

            elif accion == 'AUTO_APROBAR':
                if not dry_run:
                    self._auto_aprobar(instancia, etapa, ahora)
                auto_aprobadas += 1
                if verbosity >= 2:
                    self.stdout.write(f'    -> AUTO_APROBADO')

            elif accion == 'AUTO_RECHAZAR':
                if not dry_run:
                    self._auto_rechazar(instancia, etapa)
                auto_rechazadas += 1
                if verbosity >= 2:
                    self.stdout.write(f'    -> AUTO_RECHAZADO')

            elif accion == 'ESCALAR':
                if not dry_run:
                    self._escalar(instancia, etapa, ahora)
                escaladas += 1
                if verbosity >= 2:
                    destino = etapa.escalar_a
                    self.stdout.write(
                        f'    -> ESCALADO a {destino or "admins"}'
                    )

            procesadas += 1

        summary = (
            f'Procesadas: {procesadas} | '
            f'Auto-aprobadas: {auto_aprobadas} | '
            f'Auto-rechazadas: {auto_rechazadas} | '
            f'Escaladas: {escaladas} | '
            f'En espera: {esperadas}'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY-RUN] {summary}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Completado. {summary}'))
            logger.info(f'[escalar_vencidos] {summary}')

    # ── Private helpers ──────────────────────────────────────────────

    def _auto_aprobar(self, instancia, etapa, ahora):
        from workflows.models import PasoFlujo
        from workflows import services

        PasoFlujo.objects.create(
            instancia=instancia,
            etapa=etapa,
            aprobador=None,
            decision='AUTO_APROBADO',
            comentario=(
                f'Auto-aprobado por sistema al vencer el plazo de '
                f'{etapa.tiempo_limite_horas}h sin decision.'
            ),
        )
        siguiente = instancia.get_siguiente_etapa()
        if siguiente:
            instancia.etapa_actual = siguiente
            instancia.etapa_vence_en = (
                ahora + timedelta(hours=siguiente.tiempo_limite_horas)
                if siguiente.tiempo_limite_horas else None
            )
            instancia.save()
            services._notificar_aprobadores(instancia, siguiente, instancia.objeto)
        else:
            services._finalizar_flujo(instancia, aprobado=True)

    def _auto_rechazar(self, instancia, etapa):
        from workflows.models import PasoFlujo
        from workflows import services

        PasoFlujo.objects.create(
            instancia=instancia,
            etapa=etapa,
            aprobador=None,
            decision='AUTO_RECHAZADO',
            comentario=(
                f'Auto-rechazado por sistema al vencer el plazo de '
                f'{etapa.tiempo_limite_horas}h sin decision.'
            ),
        )
        services._finalizar_flujo(instancia, aprobado=False)

    def _escalar(self, instancia, etapa, ahora):
        from workflows.models import PasoFlujo
        from django.contrib.auth.models import User

        escalar_a = etapa.escalar_a
        if escalar_a:
            nota = (
                f'Escalado automaticamente a {escalar_a.get_full_name() or escalar_a.username} '
                f'al vencer el plazo de {etapa.tiempo_limite_horas}h.'
            )
            targets = [escalar_a]
        else:
            nota = (
                f'Escalado a administradores del sistema al vencer el plazo de '
                f'{etapa.tiempo_limite_horas}h (sin usuario alterno configurado).'
            )
            targets = list(User.objects.filter(is_superuser=True, is_active=True))

        PasoFlujo.objects.create(
            instancia=instancia,
            etapa=etapa,
            aprobador=None,
            decision='DELEGADO',
            comentario=nota,
        )

        # Extend deadline 24 h for the escalation target
        instancia.etapa_vence_en = ahora + timedelta(hours=24)
        instancia.save(update_fields=['etapa_vence_en'])

        # Notify escalation targets
        try:
            from comunicaciones.services import NotificacionService
            for dest in targets:
                NotificacionService.crear(
                    usuario=dest,
                    titulo=f'[ESCALACION] Flujo pendiente: {instancia.flujo.nombre}',
                    mensaje=(
                        f'La etapa "{etapa.nombre}" de la instancia #{instancia.pk} '
                        f'vencio sin decision. Ha sido escalada a ti. '
                        f'Tienes 24 horas para decidir.'
                    ),
                    tipo='APROBACION',
                    url=f'/workflows/bandeja/{instancia.pk}/',
                )
        except Exception as exc:
            logger.warning(f'[escalar_vencidos] Error enviando notificacion: {exc}')

    def _notificar_vencimiento(self, instancia, etapa):
        """Notify current approvers that the step is overdue but kept waiting."""
        try:
            from comunicaciones.services import NotificacionService
            for aprobador in etapa.get_aprobadores(instancia.objeto):
                NotificacionService.crear(
                    usuario=aprobador,
                    titulo=f'Recordatorio: flujo vencido pendiente de decision',
                    mensaje=(
                        f'La etapa "{etapa.nombre}" en el flujo '
                        f'"{instancia.flujo.nombre}" (#{instancia.pk}) '
                        f'ha superado su plazo y sigue esperando tu decision.'
                    ),
                    tipo='APROBACION',
                    url=f'/workflows/bandeja/{instancia.pk}/',
                )
        except Exception as exc:
            logger.warning(f'[escalar_vencidos] Error en notificacion ESPERAR: {exc}')
