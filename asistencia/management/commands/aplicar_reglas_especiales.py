"""
Reaplica ReglaEspecialPersonal sobre RegistroTareo existentes.

Cuando se crea/edita una regla especial, los registros ya generados como
FA/DS/AUTO_LIMA no se actualizan automáticamente — solo los días nuevos
que pase por `_codigo_default()` (vía `generar_faltas_auto` o
`revertir_papeleta`) verán la regla.

Este comando recorre los registros sin trabajo real ni papeleta y
reaplica `_codigo_default()`, que ya evalúa las reglas activas.

Uso:
    python manage.py aplicar_reglas_especiales
    python manage.py aplicar_reglas_especiales --personal 138
    python manage.py aplicar_reglas_especiales --fecha-ini 2026-04-01 --fecha-fin 2026-04-30
    python manage.py aplicar_reglas_especiales --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from asistencia.models import (
    FeriadoCalendario, RegistroTareo, ReglaEspecialPersonal,
)
from asistencia.services.papeletas_sync import _codigo_default


# Códigos auto que pueden ser reescritos por reglas especiales.
# Si el registro tiene fuente RELOJ con horas o MANUAL, no se toca.
FUENTES_AUTO = {'FALTA_AUTO', 'DESCANSO_SEMANAL', 'AUTO_LIMA',
                'REGLA_ESPECIAL', 'FERIADO'}


class Command(BaseCommand):
    help = 'Reaplica ReglaEspecialPersonal sobre registros existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha-ini', help='YYYY-MM-DD (inclusive)')
        parser.add_argument('--fecha-fin', help='YYYY-MM-DD (inclusive)')
        parser.add_argument('--personal', type=int, help='Filtrar por personal_id')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        from cierre.models import PeriodoCierre

        dry = opts['dry_run']
        f_ini = date.fromisoformat(opts['fecha_ini']) if opts['fecha_ini'] else None
        f_fin = date.fromisoformat(opts['fecha_fin']) if opts['fecha_fin'] else None
        personal_id = opts['personal']

        cerrados = set(
            PeriodoCierre.objects.filter(estado='CERRADO')
            .values_list('anio', 'mes')
        )

        # Solo personal con reglas activas (optimización)
        personal_con_reglas = set(
            ReglaEspecialPersonal.objects.filter(activa=True)
            .values_list('personal_id', flat=True)
            .distinct()
        )
        if not personal_con_reglas:
            self.stdout.write(self.style.WARNING(
                'No hay reglas activas. Nada que hacer.'
            ))
            return

        if personal_id:
            if personal_id not in personal_con_reglas:
                self.stdout.write(self.style.WARNING(
                    f'Personal {personal_id} no tiene reglas activas.'
                ))
                return
            personal_con_reglas = {personal_id}

        qs = (RegistroTareo.objects
              .filter(personal_id__in=personal_con_reglas,
                      fuente_codigo__in=FUENTES_AUTO,
                      personal__isnull=False)
              .select_related('personal'))

        if f_ini:
            qs = qs.filter(fecha__gte=f_ini)
        if f_fin:
            qs = qs.filter(fecha__lte=f_fin)

        # Cache feriados del rango (si f_ini/f_fin definidos, sino global)
        feriado_qs = FeriadoCalendario.objects.filter(activo=True)
        if f_ini:
            feriado_qs = feriado_qs.filter(fecha__gte=f_ini)
        if f_fin:
            feriado_qs = feriado_qs.filter(fecha__lte=f_fin)
        feriados = set(feriado_qs.values_list('fecha', flat=True))

        cambios = []
        skip_periodo_cerrado = 0
        for r in qs.iterator(chunk_size=500):
            if (r.fecha.year, r.fecha.month) in cerrados:
                skip_periodo_cerrado += 1
                continue
            es_fer = r.fecha in feriados
            nuevo_cod, nueva_fuente = _codigo_default(
                r.personal, r.fecha, es_fer,
            )
            if nuevo_cod != r.codigo_dia or nueva_fuente != r.fuente_codigo:
                cambios.append((r, nuevo_cod, nueva_fuente))

        self.stdout.write(f'Registros a actualizar: {len(cambios)}')
        self.stdout.write(f'Saltados (período cerrado): {skip_periodo_cerrado}')

        if dry:
            for r, cod, fuente in cambios[:30]:
                self.stdout.write(
                    f'  [DRY] {r.personal.apellidos_nombres} '
                    f'{r.fecha} {r.codigo_dia}/{r.fuente_codigo} → '
                    f'{cod}/{fuente}'
                )
            if len(cambios) > 30:
                self.stdout.write(f'  ... y {len(cambios) - 30} más')
            self.stdout.write(self.style.WARNING('DRY RUN — no se guardó nada.'))
            return

        if not cambios:
            self.stdout.write(self.style.SUCCESS('Nada que actualizar.'))
            return

        with transaction.atomic():
            for r, cod, fuente in cambios:
                r.codigo_dia = cod
                r.fuente_codigo = fuente
                r.save(update_fields=['codigo_dia', 'fuente_codigo'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Actualizados {len(cambios)} registros.'
        ))
