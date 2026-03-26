"""
Vistas para gestión de contratos laborales y alertas de vencimiento.
"""
from datetime import date
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from personal.models import Personal

solo_admin = user_passes_test(lambda u: u.is_superuser, login_url='login')

# ─── Umbrales de alerta ───────────────────────────────────────────────
DIAS_ALERTA_CONTRATO = [30, 15, 7]   # días antes del vencimiento
DIAS_ALERTA_PRUEBA   = [15, 7]       # días antes de fin de período de prueba


# ─────────────────────────────────────────────────────────────────────
# PANEL PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

@solo_admin
def contratos_panel(request):
    """Panel de contratos laborales con alertas y seguimiento."""
    hoy = timezone.localdate()

    activos = Personal.objects.filter(estado='Activo').select_related('subarea__area')

    # ── Contratos por vencer ──────────────────────────────────────────
    vencen_30 = activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__gte=hoy,
        fecha_fin_contrato__lte=hoy + relativedelta(days=30),
    ).order_by('fecha_fin_contrato')

    vencidos = activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__lt=hoy,
    ).order_by('fecha_fin_contrato')

    # ── Período de prueba activo ──────────────────────────────────────
    # Normal=3m, Confianza=6m, Dirección=12m
    # Buscamos quienes ingresaron hace menos de 12 meses (máximo período)
    desde_max = hoy - relativedelta(months=12)
    candidatos_prueba = activos.filter(fecha_alta__gte=desde_max)

    en_prueba = []
    for p in candidatos_prueba:
        fin_prueba = p.fecha_fin_periodo_prueba
        if fin_prueba and fin_prueba >= hoy:
            dias_restantes = (fin_prueba - hoy).days
            en_prueba.append({
                'personal': p,
                'fin_prueba': fin_prueba,
                'dias_restantes': dias_restantes,
                'alerta': dias_restantes <= 15,
            })
    en_prueba.sort(key=lambda x: x['fin_prueba'])

    # ── Estadísticas por tipo de contrato ────────────────────────────
    from django.db.models import Count
    por_tipo = (
        activos
        .exclude(tipo_contrato='')
        .values('tipo_contrato')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    sin_tipo = activos.filter(tipo_contrato='').count()

    # ── KPIs ──────────────────────────────────────────────────────────
    total_activos = activos.count()
    indefinidos   = activos.filter(tipo_contrato='INDEFINIDO').count()
    plazo_fijo    = activos.filter(tipo_contrato__in=[
        'PLAZO_FIJO', 'INICIO_ACTIVIDAD', 'NECESIDAD_MERCADO',
        'RECONVERSION_EMPRESARIAL', 'OBRA_SERVICIO', 'DISCONTINUO',
        'TEMPORADA', 'SUPLENCIA', 'EMERGENCIA',
    ]).count()

    context = {
        'hoy': hoy,
        'total_activos': total_activos,
        'indefinidos': indefinidos,
        'plazo_fijo': plazo_fijo,
        'sin_tipo': sin_tipo,
        'vencen_30': vencen_30,
        'vencidos': vencidos,
        'en_prueba': en_prueba,
        'por_tipo': por_tipo,
        # tabs activos según query param
        'tab_activo': request.GET.get('tab', 'vencimientos'),
    }
    return render(request, 'personal/contratos_panel.html', context)


# ─────────────────────────────────────────────────────────────────────
# LISTA COMPLETA DE CONTRATOS
# ─────────────────────────────────────────────────────────────────────

@solo_admin
def contratos_lista(request):
    """Lista de todos los empleados con sus datos de contrato."""
    hoy = timezone.localdate()

    qs = Personal.objects.filter(estado='Activo').select_related('subarea__area').order_by('apellidos_nombres')

    # Filtros
    buscar = request.GET.get('buscar', '').strip()
    tipo_f = request.GET.get('tipo', '')
    estado_f = request.GET.get('estado_contrato', '')  # VIGENTE / VENCIDO / INDEFINIDO / SIN_DATOS

    if buscar:
        qs = qs.filter(
            Q(apellidos_nombres__icontains=buscar) | Q(nro_doc__icontains=buscar)
        )
    if tipo_f:
        qs = qs.filter(tipo_contrato=tipo_f)

    if estado_f == 'VIGENTE':
        qs = qs.filter(fecha_fin_contrato__gte=hoy)
    elif estado_f == 'VENCIDO':
        qs = qs.filter(fecha_fin_contrato__lt=hoy)
    elif estado_f == 'INDEFINIDO':
        qs = qs.filter(tipo_contrato='INDEFINIDO')
    elif estado_f == 'SIN_DATOS':
        qs = qs.filter(tipo_contrato='')

    # Anotar días para vencimiento
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Calcular días restantes para cada empleado en la página
    empleados = []
    for p in page_obj:
        dias = None
        estado_contrato = 'INDEFINIDO' if p.tipo_contrato == 'INDEFINIDO' else ''
        if p.fecha_fin_contrato:
            dias = (p.fecha_fin_contrato - hoy).days
            if dias < 0:
                estado_contrato = 'VENCIDO'
            elif dias <= 30:
                estado_contrato = 'URGENTE'
            else:
                estado_contrato = 'VIGENTE'
        elif not p.tipo_contrato:
            estado_contrato = 'SIN_DATOS'
        empleados.append({
            'personal': p,
            'dias_restantes': dias,
            'estado_contrato': estado_contrato,
        })

    context = {
        'empleados': empleados,
        'page_obj': page_obj,
        'buscar': buscar,
        'tipo_f': tipo_f,
        'estado_f': estado_f,
        'tipos': Personal.TIPO_CONTRATO_CHOICES,
        'hoy': hoy,
    }
    return render(request, 'personal/contratos_lista.html', context)


# ─────────────────────────────────────────────────────────────────────
# EDITAR CONTRATO DE UN EMPLEADO
# ─────────────────────────────────────────────────────────────────────

@solo_admin
def contrato_editar(request, pk):
    """Edita los campos de contrato de un empleado."""
    personal = get_object_or_404(Personal, pk=pk)

    if request.method == 'POST':
        personal.tipo_contrato         = request.POST.get('tipo_contrato', '')
        personal.renovacion_automatica = bool(request.POST.get('renovacion_automatica'))
        personal.observaciones_contrato = request.POST.get('observaciones_contrato', '')

        fecha_inicio = request.POST.get('fecha_inicio_contrato', '').strip()
        fecha_fin    = request.POST.get('fecha_fin_contrato', '').strip()

        personal.fecha_inicio_contrato = date.fromisoformat(fecha_inicio) if fecha_inicio else None
        personal.fecha_fin_contrato    = date.fromisoformat(fecha_fin) if fecha_fin else None

        personal.save(update_fields=[
            'tipo_contrato', 'fecha_inicio_contrato', 'fecha_fin_contrato',
            'renovacion_automatica', 'observaciones_contrato',
        ])
        messages.success(request, f"Contrato de {personal.apellidos_nombres} actualizado.")
        return redirect('contratos_panel')

    context = {
        'personal': personal,
        'tipos': Personal.TIPO_CONTRATO_CHOICES,
    }
    return render(request, 'personal/contrato_editar.html', context)


# ─────────────────────────────────────────────────────────────────────
# API: datos para dashboard de contratos (AJAX)
# ─────────────────────────────────────────────────────────────────────

@solo_admin
def contratos_api_stats(request):
    """JSON con KPIs de contratos para gráficos."""
    hoy = timezone.localdate()
    activos = Personal.objects.filter(estado='Activo')

    por_tipo = {}
    for val, lbl in Personal.TIPO_CONTRATO_CHOICES:
        c = activos.filter(tipo_contrato=val).count()
        if c:
            por_tipo[lbl] = c

    return JsonResponse({
        'por_tipo': por_tipo,
        'vencen_7': activos.filter(
            fecha_fin_contrato__gte=hoy,
            fecha_fin_contrato__lte=hoy + relativedelta(days=7)
        ).count(),
        'vencen_30': activos.filter(
            fecha_fin_contrato__gte=hoy,
            fecha_fin_contrato__lte=hoy + relativedelta(days=30)
        ).count(),
        'vencidos': activos.filter(fecha_fin_contrato__lt=hoy).count(),
    })
