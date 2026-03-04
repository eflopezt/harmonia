"""
Servicio de auditoría — funciones para registrar cambios en el sistema.

Uso:
    from core.audit import log_create, log_update, log_delete

    # En una vista:
    log_create(request, personal)
    log_update(request, personal, cambios={'cargo': {'old': 'Analista', 'new': 'Jefe'}})
    log_delete(request, personal)

    # Sin request (ej. management commands):
    log_create(None, personal, usuario=user)
"""
import threading

from django.contrib.contenttypes.models import ContentType

from core.models import AuditLog

# Thread-local storage para request actual (set por middleware)
_thread_locals = threading.local()


def get_current_request():
    """Retorna el request del thread actual (set por AuditMiddleware)."""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Guarda el request en thread-local storage."""
    _thread_locals.request = request


def _get_client_ip(request):
    """Extrae la IP real del cliente."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_create(request, instance, descripcion='', usuario=None):
    """Registra la creación de un objeto."""
    if request is None:
        request = get_current_request()

    AuditLog.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
        accion='CREATE',
        descripcion=descripcion or f'Creado: {instance}',
        cambios={},
        usuario=usuario or (request.user if request and request.user.is_authenticated else None),
        ip_address=_get_client_ip(request),
    )


def log_update(request, instance, cambios, descripcion=''):
    """Registra la modificación de un objeto.

    Args:
        cambios: dict con {campo: {'old': valor_ant, 'new': valor_nuevo}}
    """
    if not cambios:
        return  # No registrar si no hay cambios

    if request is None:
        request = get_current_request()

    # Serializar valores para JSON
    cambios_safe = {}
    for campo, vals in cambios.items():
        cambios_safe[campo] = {
            'old': _serialize(vals.get('old')),
            'new': _serialize(vals.get('new')),
        }

    AuditLog.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
        accion='UPDATE',
        descripcion=descripcion or f'Modificado: {instance}',
        cambios=cambios_safe,
        usuario=request.user if request and request.user.is_authenticated else None,
        ip_address=_get_client_ip(request),
    )


def log_delete(request, instance, descripcion=''):
    """Registra la eliminación/anulación de un objeto."""
    if request is None:
        request = get_current_request()

    AuditLog.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
        accion='DELETE',
        descripcion=descripcion or f'Eliminado: {instance}',
        cambios={},
        usuario=request.user if request and request.user.is_authenticated else None,
        ip_address=_get_client_ip(request),
    )


def get_audit_log(instance, limit=50):
    """Retorna el historial de auditoría de un objeto."""
    ct = ContentType.objects.get_for_model(instance)
    return AuditLog.objects.filter(
        content_type=ct,
        object_id=instance.pk,
    ).select_related('usuario')[:limit]


def _serialize(value):
    """Convierte un valor a formato serializable para JSON."""
    if value is None:
        return None
    from datetime import date, datetime
    from decimal import Decimal
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'pk'):
        return str(value)
    return value
