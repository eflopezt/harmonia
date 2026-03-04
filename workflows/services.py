import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

logger = logging.getLogger(__name__)


def iniciar_flujo(objeto, solicitante=None):
    """Busca si existe un FlujoTrabajo activo para este objeto/estado y lo inicia."""
    from .models import FlujoTrabajo, InstanciaFlujo

    ct     = ContentType.objects.get_for_model(objeto.__class__)
    estado = getattr(objeto, 'estado', None)
    if not estado:
        return None

    flujo = FlujoTrabajo.objects.filter(
        content_type=ct,
        campo_trigger='estado',
        valor_trigger=estado,
        activo=True,
    ).first()

    if not flujo:
        return None

    existente = InstanciaFlujo.objects.filter(
        flujo=flujo, content_type=ct, object_id=objeto.pk, estado='EN_PROCESO',
    ).first()
    if existente:
        return existente

    primera_etapa = flujo.etapas.order_by('orden').first()

    vence_en = None
    if primera_etapa and primera_etapa.tiempo_limite_horas:
        vence_en = timezone.now() + timedelta(hours=primera_etapa.tiempo_limite_horas)

    instancia = InstanciaFlujo.objects.create(
        flujo=flujo, content_type=ct, object_id=objeto.pk,
        etapa_actual=primera_etapa, estado='EN_PROCESO',
        solicitante=solicitante, etapa_vence_en=vence_en,
    )

    if primera_etapa:
        _notificar_aprobadores(instancia, primera_etapa, objeto)

    logger.info(f'[Workflow] Flujo iniciado: #{instancia.pk}')
    return instancia


def decidir(instancia, usuario, decision, comentario=''):
    """El usuario toma una decision en la etapa actual. decision: APROBADO|RECHAZADO"""
    from .models import PasoFlujo

    if not instancia.puede_aprobar(usuario):
        logger.warning(f'[Workflow] Sin permiso: {usuario} en instancia #{instancia.pk}')
        return False

    if instancia.etapa_actual and instancia.etapa_actual.requiere_comentario:
        if not comentario.strip():
            raise ValueError('Esta etapa requiere un comentario.')

    PasoFlujo.objects.create(
        instancia=instancia, etapa=instancia.etapa_actual,
        aprobador=usuario, decision=decision, comentario=comentario,
    )

    if decision == 'APROBADO':
        siguiente = instancia.get_siguiente_etapa()
        if siguiente:
            instancia.etapa_actual   = siguiente
            instancia.etapa_vence_en = (
                timezone.now() + timedelta(hours=siguiente.tiempo_limite_horas)
                if siguiente.tiempo_limite_horas else None
            )
            instancia.save()
            _notificar_aprobadores(instancia, siguiente, instancia.objeto)
        else:
            _finalizar_flujo(instancia, aprobado=True)
    else:
        _finalizar_flujo(instancia, aprobado=False)

    return True


def cancelar_flujo(instancia, motivo=''):
    """Cancela un flujo en proceso."""
    from .models import PasoFlujo

    if instancia.estado != 'EN_PROCESO':
        return False

    PasoFlujo.objects.create(
        instancia=instancia, etapa=instancia.etapa_actual,
        decision='CANCELADO', comentario=motivo,
    )
    instancia.estado        = 'CANCELADO'
    instancia.completado_en = timezone.now()
    instancia.save()
    return True


def get_pendientes_usuario(usuario):
    """Retorna QuerySet de InstanciaFlujo pendientes donde el usuario puede decidir."""
    from .models import InstanciaFlujo, EtapaFlujo
    from django.db.models import Q

    etapa_q = Q(tipo_aprobador='SUPERUSER') if usuario.is_superuser else Q(pk__in=[])
    etapa_q |= Q(tipo_aprobador='USUARIO', aprobador_usuario=usuario)

    if usuario.groups.exists():
        etapa_q |= Q(
            tipo_aprobador='GRUPO_DJANGO',
            aprobador_grupo__in=usuario.groups.all(),
        )

    etapas_ids = EtapaFlujo.objects.filter(etapa_q).values_list('pk', flat=True)

    return InstanciaFlujo.objects.filter(
        estado='EN_PROCESO',
        etapa_actual_id__in=etapas_ids,
    ).select_related('flujo', 'etapa_actual', 'solicitante', 'content_type').order_by('-iniciado_en')


def verificar_vencimientos():
    """Procesa instancias vencidas segun su accion_vencimiento. Llamar desde Celery beat."""
    from .models import InstanciaFlujo, PasoFlujo

    ahora    = timezone.now()
    vencidas = InstanciaFlujo.objects.filter(
        estado='EN_PROCESO', etapa_vence_en__lt=ahora, etapa_actual__isnull=False,
    ).select_related('etapa_actual', 'flujo')

    procesadas = 0
    for instancia in vencidas:
        accion = instancia.etapa_actual.accion_vencimiento
        if accion == 'ESPERAR':
            continue
        elif accion == 'AUTO_APROBAR':
            PasoFlujo.objects.create(
                instancia=instancia, etapa=instancia.etapa_actual,
                decision='AUTO_APROBADO',
                comentario=f'Auto-aprobado por vencimiento ({instancia.etapa_actual.tiempo_limite_horas}h)',
            )
            siguiente = instancia.get_siguiente_etapa()
            if siguiente:
                instancia.etapa_actual   = siguiente
                instancia.etapa_vence_en = (
                    ahora + timedelta(hours=siguiente.tiempo_limite_horas)
                    if siguiente.tiempo_limite_horas else None
                )
                instancia.save()
            else:
                _finalizar_flujo(instancia, aprobado=True)
        elif accion == 'AUTO_RECHAZAR':
            PasoFlujo.objects.create(
                instancia=instancia, etapa=instancia.etapa_actual,
                decision='AUTO_RECHAZADO',
                comentario=f'Auto-rechazado por vencimiento ({instancia.etapa_actual.tiempo_limite_horas}h)',
            )
            _finalizar_flujo(instancia, aprobado=False)
        elif accion == 'ESCALAR':
            escalar_a = instancia.etapa_actual.escalar_a
            if escalar_a:
                instancia.etapa_actual.aprobador_usuario = escalar_a
                instancia.etapa_actual.tipo_aprobador    = 'USUARIO'
                instancia.etapa_vence_en = ahora + timedelta(hours=24)
                instancia.save()
                PasoFlujo.objects.create(
                    instancia=instancia, etapa=instancia.etapa_actual,
                    decision='DELEGADO', comentario=f'Escalado a {escalar_a} por vencimiento',
                )
        procesadas += 1

    return procesadas


def _finalizar_flujo(instancia, aprobado):
    """Actualiza el objeto relacionado y cierra la instancia."""
    flujo  = instancia.flujo
    objeto = instancia.objeto

    if objeto:
        campo = flujo.campo_resultado
        valor = flujo.valor_aprobado if aprobado else flujo.valor_rechazado
        try:
            setattr(objeto, campo, valor)
            objeto.save(update_fields=[campo])
        except Exception as e:
            logger.error(f'[Workflow] Error actualizando {objeto}: {e}')

    instancia.estado        = 'APROBADO' if aprobado else 'RECHAZADO'
    instancia.completado_en = timezone.now()
    instancia.etapa_actual  = None
    instancia.save()

    if flujo.notificar_email and instancia.solicitante:
        _notificar_solicitante_resultado(instancia, aprobado)

    logger.info(f'[Workflow] Flujo #{instancia.pk} {"APROBADO" if aprobado else "RECHAZADO"}')


def _notificar_aprobadores(instancia, etapa, objeto):
    try:
        from comunicaciones.services import NotificacionService
        for aprobador in etapa.get_aprobadores(objeto):
            NotificacionService.crear(
                usuario=aprobador,
                titulo=f'Pendiente de aprobacion: {instancia.flujo.nombre}',
                mensaje=f'Solicitud pendiente en "{etapa.nombre}".',
                tipo='APROBACION',
                url='/workflows/bandeja/',
            )
    except Exception as e:
        logger.warning(f'[Workflow] Error notificando aprobadores: {e}')


def _notificar_solicitante_resultado(instancia, aprobado):
    try:
        from comunicaciones.services import NotificacionService
        txt = 'aprobada' if aprobado else 'rechazada'
        NotificacionService.crear(
            usuario=instancia.solicitante,
            titulo=f'Tu solicitud fue {txt}',
            mensaje=f'Tu solicitud en "{instancia.flujo.nombre}" fue {txt}.',
            tipo='APROBACION', url='/',
        )
    except Exception as e:
        logger.warning(f'[Workflow] Error notificando solicitante: {e}')
