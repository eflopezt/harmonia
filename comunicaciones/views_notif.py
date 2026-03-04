"""
Vistas AJAX para notificaciones in-app (header badge + dropdown).
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notificacion


@login_required
def notificaciones_json(request):
    """
    Retorna las últimas 8 notificaciones IN_APP del usuario.
    Incluye conteo de no leídas para el badge.
    """
    try:
        personal = request.user.personal_data
    except Exception:
        return JsonResponse({'count': 0, 'items': []})

    qs = Notificacion.objects.filter(
        destinatario=personal,
        tipo='IN_APP',
    ).order_by('-creado_en')[:8]

    no_leidas = Notificacion.objects.filter(
        destinatario=personal,
        tipo='IN_APP',
        estado__in=['PENDIENTE', 'ENVIADA'],
    ).count()

    items = []
    for n in qs:
        meta = n.metadata or {}
        items.append({
            'id':      n.pk,
            'asunto':  n.asunto,
            'leida':   n.estado == 'LEIDA',
            'icono':   meta.get('icono', 'fa-bell'),
            'color':   meta.get('color', '#0f766e'),
            'url':     meta.get('url', '#'),
            'tiempo':  _tiempo_relativo(n.creado_en),
        })

    return JsonResponse({'count': no_leidas, 'items': items})


@login_required
@require_POST
def notificacion_marcar_leida(request, pk):
    """Marca una notificación como leída."""
    try:
        personal = request.user.personal_data
    except Exception:
        return JsonResponse({'ok': False})

    updated = Notificacion.objects.filter(
        pk=pk, destinatario=personal,
    ).update(estado='LEIDA', leida_en=timezone.now())
    return JsonResponse({'ok': bool(updated)})


@login_required
@require_POST
def notificaciones_marcar_todas(request):
    """Marca todas las notificaciones pendientes como leídas."""
    try:
        personal = request.user.personal_data
    except Exception:
        return JsonResponse({'ok': False})

    count = Notificacion.objects.filter(
        destinatario=personal,
        tipo='IN_APP',
        estado__in=['PENDIENTE', 'ENVIADA'],
    ).update(estado='LEIDA', leida_en=timezone.now())
    return JsonResponse({'ok': True, 'count': count})


@login_required
def notificaciones_api_count(request):
    """
    API: retorna {count: N} — cantidad de notificaciones IN_APP no leídas del usuario.
    Usada por el badge del header.
    """
    try:
        personal = request.user.personal_data
    except Exception:
        return JsonResponse({'count': 0})

    count = Notificacion.objects.filter(
        destinatario=personal,
        tipo='IN_APP',
        estado__in=['PENDIENTE', 'ENVIADA'],
    ).count()
    return JsonResponse({'count': count})


@login_required
def notificaciones_api_recientes(request):
    """
    API: retorna las últimas 5 notificaciones IN_APP no leídas y las marca como leídas.
    Formato: {items: [{titulo, mensaje, url, tipo, creado_en_humanized}]}
    """
    try:
        personal = request.user.personal_data
    except Exception:
        return JsonResponse({'items': []})

    qs = Notificacion.objects.filter(
        destinatario=personal,
        tipo='IN_APP',
        estado__in=['PENDIENTE', 'ENVIADA'],
    ).order_by('-creado_en')[:5]

    items = []
    ids_leidas = []
    for n in qs:
        meta = n.metadata or {}
        items.append({
            'id': n.pk,
            'titulo': n.asunto,
            'mensaje': n.cuerpo or '',
            'url': meta.get('url', '#'),
            'tipo': meta.get('tipo_notificacion', 'INFO'),
            'icono': meta.get('icono', 'fa-bell'),
            'color': meta.get('color', '#0f766e'),
            'creado_en_humanized': _tiempo_relativo(n.creado_en),
        })
        ids_leidas.append(n.pk)

    # Marcar como leídas
    if ids_leidas:
        Notificacion.objects.filter(pk__in=ids_leidas).update(
            estado='LEIDA', leida_en=timezone.now()
        )

    return JsonResponse({'items': items})


def _tiempo_relativo(dt) -> str:
    """Retorna string legible 'hace X min/hora/dias'."""
    from django.utils import timezone as tz
    delta = tz.now() - dt
    s = int(delta.total_seconds())
    if s < 60:
        return 'ahora'
    elif s < 3600:
        return f'hace {s // 60}m'
    elif s < 86400:
        return f'hace {s // 3600}h'
    else:
        return f'hace {delta.days}d'
