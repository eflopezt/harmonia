"""Workflow signals - intercepta cambios de estado en modelos configurados."""
import logging
from django.db.models.signals import post_save

logger = logging.getLogger(__name__)


def _check_workflow_trigger(sender, instance, created, **kwargs):
    """Verifica si este save activa un workflow configurado."""
    try:
        from .services import iniciar_flujo
        from django.contrib.auth.models import User
        solicitante = (
            getattr(instance, 'solicitado_por', None) or
            getattr(instance, 'creado_por', None) or
            getattr(instance, 'usuario', None)
        )
        if solicitante and not isinstance(solicitante, User):
            solicitante = None
        iniciar_flujo(instance, solicitante=solicitante)
    except Exception as e:
        logger.warning(f'[Workflow Signal] Error en trigger para {sender}: {e}')


def conectar_flujos_activos():
    """
    Conecta senales post_save a todos los modelos con flujos activos.
    Llamar desde AppConfig.ready() despues de que la DB este disponible.
    """
    try:
        from .models import FlujoTrabajo

        flujos = FlujoTrabajo.objects.filter(activo=True).select_related('content_type')
        for flujo in flujos:
            model_class = flujo.content_type.model_class()
            if model_class:
                post_save.connect(
                    _check_workflow_trigger,
                    sender=model_class,
                    weak=False,
                    dispatch_uid=f'workflow_{flujo.pk}_{model_class.__name__}',
                )
                logger.info(f'[Workflow] Signal conectado: {model_class.__name__} -> {flujo.nombre}')
    except Exception as e:
        logger.warning(f'[Workflow] No se pudieron conectar signals: {e}')
