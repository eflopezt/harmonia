"""Tareas Celery para integraciones."""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger('asistencia')


@shared_task(name='integraciones.tasks.sync_synkro_auto')
def sync_synkro_auto():
    """Corrida automática del sync con Synkro RRHH.

    No-op si SYNKRO_HOST no está configurado (BD secundaria opcional).
    """
    if 'synkro' not in settings.DATABASES:
        return 'skipped: synkro DB not configured'

    from integraciones.services.synkro_sync import run_sync
    log = run_sync(origen='AUTO', ventana_picados_dias=7)
    return (f'estado={log.estado} dur={log.duracion_segundos}s '
            f'pap_c={log.papeletas_creadas} pap_u={log.papeletas_actualizadas} '
            f'reg_c={log.registros_tareo_creados} reg_u={log.registros_tareo_actualizados}')


@shared_task(name='integraciones.tasks.sync_synkro_manual')
def sync_synkro_manual(usuario_id: int | None = None,
                       ventana_dias: int = 60):
    """Sync disparado manualmente desde el ERP (botón).

    Ventana más amplia que la automática para cuando se hace por demanda.
    """
    if 'synkro' not in settings.DATABASES:
        return {'estado': 'ERROR', 'mensaje': 'Synkro no configurado en este servidor'}

    from django.contrib.auth import get_user_model
    from integraciones.services.synkro_sync import run_sync

    user = None
    if usuario_id:
        try:
            user = get_user_model().objects.get(pk=usuario_id)
        except Exception:
            pass

    log = run_sync(origen='MANUAL', usuario=user,
                   ventana_picados_dias=ventana_dias)
    return {
        'estado': log.estado,
        'log_id': log.id,
        'duracion': log.duracion_segundos,
        'papeletas_creadas': log.papeletas_creadas,
        'papeletas_actualizadas': log.papeletas_actualizadas,
        'registros_tareo_creados': log.registros_tareo_creados,
        'registros_tareo_actualizados': log.registros_tareo_actualizados,
        'feriados_creados': log.feriados_creados,
        'personas_no_encontradas': log.personas_no_encontradas,
        'error': log.error_mensaje,
    }
