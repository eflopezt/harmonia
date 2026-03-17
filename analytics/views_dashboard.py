"""
Dashboard Personalizable — API Views.

Endpoints para el dashboard drag-and-drop:
- dashboard_config: GET/POST del layout del usuario
- widget_data: GET datos de un widget individual (AJAX)
- widget_catalog: GET catálogo de widgets disponibles
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import DashboardLayout
from .widget_engine import get_widget_data, get_catalog, get_default_layout, WIDGET_CATALOG

logger = logging.getLogger('analytics.views_dashboard')


@login_required
@require_http_methods(["GET", "POST"])
@ensure_csrf_cookie
def dashboard_config(request):
    """
    GET:  Retorna el layout actual del usuario (widget_ids ordenados).
    POST: Guarda el layout del usuario (widget_ids + config).
    """
    if request.method == 'GET':
        try:
            layout = DashboardLayout.objects.get(user=request.user)
            widget_ids = layout.widget_ids
            config = layout.config
        except DashboardLayout.DoesNotExist:
            widget_ids = get_default_layout(request.user)
            config = {}

        # Filtrar widgets que ya no existan en el catálogo
        valid_ids = [wid for wid in widget_ids if wid in WIDGET_CATALOG]

        # Filtrar por permisos
        if not request.user.is_superuser:
            valid_ids = [
                wid for wid in valid_ids
                if not WIDGET_CATALOG[wid].get('requires_superuser')
            ]

        return JsonResponse({
            'widget_ids': valid_ids,
            'config': config,
        })

    # POST: guardar layout
    try:
        body = json.loads(request.body)
        widget_ids = body.get('widget_ids', [])
        config = body.get('config', {})

        # Validar que los IDs sean strings válidos del catálogo
        valid_ids = [wid for wid in widget_ids if isinstance(wid, str) and wid in WIDGET_CATALOG]

        layout, created = DashboardLayout.objects.update_or_create(
            user=request.user,
            defaults={'widget_ids': valid_ids, 'config': config},
        )

        return JsonResponse({
            'ok': True,
            'widget_ids': valid_ids,
            'created': created,
        })
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def widget_data(request):
    """
    GET /analytics/dashboard/widget/?id=headcount_total
    Retorna los datos de un widget específico (para carga AJAX).
    """
    widget_id = request.GET.get('id', '')
    if not widget_id:
        return JsonResponse({'error': 'Parámetro "id" requerido'}, status=400)

    result = get_widget_data(widget_id, request.user)
    return JsonResponse(result)


@login_required
@require_GET
def widget_catalog(request):
    """
    GET /analytics/dashboard/catalog/
    Retorna el catálogo completo de widgets disponibles para el usuario.
    """
    catalog = get_catalog(request.user)
    # Agrupar por categoría
    categories = {}
    for w in catalog:
        cat = w['category']
        if cat not in categories:
            categories[cat] = {
                'label': _category_label(cat),
                'icon': _category_icon(cat),
                'widgets': [],
            }
        categories[cat]['widgets'].append(w)

    return JsonResponse({
        'widgets': catalog,
        'categories': categories,
    })


def _category_label(cat):
    labels = {
        'personal': 'Personal',
        'asistencia': 'Asistencia',
        'nominas': 'Nominas',
        'vacaciones': 'Vacaciones',
        'aprobaciones': 'Aprobaciones',
        'analytics': 'Analytics',
        'general': 'General',
    }
    return labels.get(cat, cat.title())


def _category_icon(cat):
    icons = {
        'personal': 'fa-users',
        'asistencia': 'fa-fingerprint',
        'nominas': 'fa-coins',
        'vacaciones': 'fa-umbrella-beach',
        'aprobaciones': 'fa-tasks',
        'analytics': 'fa-chart-line',
        'general': 'fa-th-large',
    }
    return icons.get(cat, 'fa-cube')
