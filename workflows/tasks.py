"""
Tareas Celery para el motor de Workflows.

Tareas periódicas:
  - verificar_vencimientos_workflows  → cada hora, vence etapas pasadas de plazo
  - notificar_pendientes_workflows    → cada mañana, recuerda aprobadores con pasos pendientes
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('workflows')


@shared_task(bind=True, name='workflows.verificar_vencimientos', max_retries=1)
def verificar_vencimientos_workflows(self):
    """
    Recorre todas las instancias ACTIVAS cuya etapa_vence_en ya pasó
    y aplica la acción configurada (AUTO_APROBAR / AUTO_RECHAZAR / ESCALAR).

    Programar: cada hora (crontab(minute=0)).
    """
    try:
        from workflows.services import verificar_vencimientos
        resultado = verificar_vencimientos()
        logger.info(f'Vencimientos procesados: {resultado}')
        return resultado
    except Exception as exc:
        logger.error(f'Error en verificar_vencimientos_workflows: {exc}')
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, name='workflows.notificar_pendientes', max_retries=1)
def notificar_pendientes_workflows(self):
    """
    Envía email/notificación a cada aprobador que tiene pasos pendientes.

    Programar: 08:00 cada día laborable (crontab(hour=8, minute=0, day_of_week='1-5')).
    """
    try:
        from workflows.models import InstanciaFlujo, PasoFlujo
        from comunicaciones.services import NotificacionService
        from django.contrib.auth import get_user_model
        from django.db.models import Count

        User = get_user_model()

        instancias_activas = InstanciaFlujo.objects.filter(
            estado='ACTIVO'
        ).select_related('etapa_actual', 'flujo')

        notificados = 0
        for instancia in instancias_activas:
            try:
                aprobadores = instancia.etapa_actual.get_aprobadores(instancia.objeto)
                for aprobador in aprobadores:
                    if aprobador.correo_corporativo or aprobador.email:
                        NotificacionService.crear(
                            usuario=aprobador,
                            tipo='SISTEMA',
                            titulo='Aprobación pendiente',
                            mensaje=(
                                f'Tienes una aprobación pendiente: '
                                f'"{instancia.flujo.nombre}" — '
                                f'Etapa: {instancia.etapa_actual.nombre}. '
                                f'Ingresa a Harmoni → Bandeja de Workflows para revisar.'
                            ),
                            url_destino='/workflows/',
                        )
                        notificados += 1
            except Exception as e:
                logger.warning(f'Error notificando instancia {instancia.pk}: {e}')

        logger.info(f'Notificaciones pendientes workflows enviadas: {notificados}')
        return {'notificados': notificados}

    except Exception as exc:
        logger.error(f'Error en notificar_pendientes_workflows: {exc}')
        raise self.retry(exc=exc, countdown=600)
