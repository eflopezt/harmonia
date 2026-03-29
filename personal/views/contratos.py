"""
Vistas para gestión de contratos laborales, adendas, renovaciones y alertas.
"""
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, Value, CharField
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

from personal.models import Personal, Contrato, RenovacionContrato, Adenda
from personal.forms import ContratoForm, AdendaForm, RenovacionContratoForm

solo_admin = user_passes_test(lambda u: u.is_superuser, login_url='login')

# ─── Estilos Excel ────────────────────────────────────────────────────────────
HEADER_FILL  = PatternFill("solid", fgColor="0D2B27")
HEADER_FONT  = Font(color="FFFFFF", bold=True, size=10)
ALT_FILL     = PatternFill("solid", fgColor="F0FDFA")
THIN_BORDER  = Border(
    left=Side(style='thin', color='CCCCCC'),
    right=Side(style='thin', color='CCCCCC'),
    top=Side(style='thin', color='CCCCCC'),
    bottom=Side(style='thin', color='CCCCCC'),
)

# ─── Umbrales de alerta ───────────────────────────────────────────────
DIAS_ALERTA_CONTRATO = [30, 15, 7]
DIAS_ALERTA_PRUEBA   = [15, 7]


# ═════════════════════════════════════════════════════════════════════════════
# PANEL PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

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

    vencen_60 = activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__gt=hoy + relativedelta(days=30),
        fecha_fin_contrato__lte=hoy + relativedelta(days=60),
    ).order_by('fecha_fin_contrato')

    vencen_90 = activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__gt=hoy + relativedelta(days=60),
        fecha_fin_contrato__lte=hoy + relativedelta(days=90),
    ).order_by('fecha_fin_contrato')

    vencidos = activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__lt=hoy,
    ).order_by('fecha_fin_contrato')

    sin_contrato = activos.filter(tipo_contrato='').count()

    # ── Período de prueba activo ──────────────────────────────────────
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

    # ── Últimas adendas y renovaciones (modelo nuevo) ────────────────
    ultimas_adendas = Adenda.objects.select_related(
        'contrato__personal',
    ).order_by('-creado_en')[:5]

    ultimas_renovaciones = RenovacionContrato.objects.select_related(
        'contrato_original__personal',
    ).order_by('-creado_en')[:5]

    context = {
        'hoy': hoy,
        'total_activos': total_activos,
        'indefinidos': indefinidos,
        'plazo_fijo': plazo_fijo,
        'sin_tipo': sin_tipo,
        'sin_contrato': sin_contrato,
        'vencen_30': vencen_30,
        'vencen_60': vencen_60,
        'vencen_90': vencen_90,
        'vencidos': vencidos,
        'en_prueba': en_prueba,
        'por_tipo': por_tipo,
        'ultimas_adendas': ultimas_adendas,
        'ultimas_renovaciones': ultimas_renovaciones,
        'tab_activo': request.GET.get('tab', 'vencimientos'),
    }
    return render(request, 'personal/contratos_panel.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# LISTA COMPLETA DE CONTRATOS
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contratos_lista(request):
    """Lista de todos los empleados con sus datos de contrato."""
    hoy = timezone.localdate()

    qs = Personal.objects.filter(estado='Activo').select_related('subarea__area').order_by('apellidos_nombres')

    # Filtros
    buscar = request.GET.get('buscar', '').strip()
    tipo_f = request.GET.get('tipo', '')
    estado_f = request.GET.get('estado_contrato', '')
    area_f = request.GET.get('area', '')
    vencimiento_f = request.GET.get('vencimiento', '')  # 30, 60, 90

    if buscar:
        qs = qs.filter(
            Q(apellidos_nombres__icontains=buscar) | Q(nro_doc__icontains=buscar)
        )
    if tipo_f:
        qs = qs.filter(tipo_contrato=tipo_f)
    if area_f:
        qs = qs.filter(subarea__area_id=area_f)

    if estado_f == 'VIGENTE':
        qs = qs.filter(fecha_fin_contrato__gte=hoy)
    elif estado_f == 'VENCIDO':
        qs = qs.filter(fecha_fin_contrato__lt=hoy)
    elif estado_f == 'INDEFINIDO':
        qs = qs.filter(tipo_contrato='INDEFINIDO')
    elif estado_f == 'SIN_DATOS':
        qs = qs.filter(tipo_contrato='')

    if vencimiento_f:
        try:
            dias_lim = int(vencimiento_f)
            qs = qs.filter(
                fecha_fin_contrato__isnull=False,
                fecha_fin_contrato__gte=hoy,
                fecha_fin_contrato__lte=hoy + relativedelta(days=dias_lim),
            )
        except ValueError:
            pass

    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

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

    from personal.models import Area
    areas = Area.objects.filter(activa=True).order_by('nombre')

    context = {
        'empleados': empleados,
        'page_obj': page_obj,
        'buscar': buscar,
        'tipo_f': tipo_f,
        'estado_f': estado_f,
        'area_f': area_f,
        'vencimiento_f': vencimiento_f,
        'tipos': Personal.TIPO_CONTRATO_CHOICES,
        'areas': areas,
        'hoy': hoy,
        'total_resultados': paginator.count,
    }
    return render(request, 'personal/contratos_lista.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# DETALLE DE CONTRATO DE UN EMPLEADO
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contrato_detalle(request, pk):
    """Detalle del contrato de un empleado con timeline de adendas y renovaciones."""
    personal = get_object_or_404(Personal, pk=pk)
    hoy = timezone.localdate()

    # Contratos del modelo nuevo (si existen)
    contratos = Contrato.objects.filter(
        personal=personal
    ).prefetch_related('adendas', 'renovaciones_salientes__contrato_nuevo').order_by('-fecha_inicio')

    # Timeline: combinar adendas y renovaciones ordenadas por fecha
    timeline = []
    for c in contratos:
        timeline.append({
            'tipo': 'contrato',
            'fecha': c.fecha_inicio,
            'titulo': f'Contrato {c.get_tipo_contrato_display()}',
            'detalle': f'{c.fecha_inicio.strftime("%d/%m/%Y")} — {c.fecha_fin.strftime("%d/%m/%Y") if c.fecha_fin else "Indefinido"}',
            'estado': c.estado,
            'objeto': c,
        })
        for adenda in c.adendas.all():
            timeline.append({
                'tipo': 'adenda',
                'fecha': adenda.fecha,
                'titulo': f'Adenda: {adenda.get_tipo_modificacion_display()}',
                'detalle': adenda.detalle[:100],
                'estado': '',
                'objeto': adenda,
            })
        for ren in c.renovaciones_salientes.all():
            timeline.append({
                'tipo': 'renovacion',
                'fecha': ren.fecha_renovacion,
                'titulo': 'Renovación de contrato',
                'detalle': ren.motivo[:100] if ren.motivo else 'Sin motivo registrado',
                'estado': '',
                'objeto': ren,
            })
    timeline.sort(key=lambda x: x['fecha'], reverse=True)

    # Info del contrato actual (campos en Personal)
    dias_restantes = None
    estado_contrato = 'INDEFINIDO' if personal.tipo_contrato == 'INDEFINIDO' else ''
    if personal.fecha_fin_contrato:
        dias_restantes = (personal.fecha_fin_contrato - hoy).days
        if dias_restantes < 0:
            estado_contrato = 'VENCIDO'
        elif dias_restantes <= 30:
            estado_contrato = 'URGENTE'
        else:
            estado_contrato = 'VIGENTE'
    elif not personal.tipo_contrato:
        estado_contrato = 'SIN_DATOS'

    contrato_vigente = contratos.filter(estado='VIGENTE').first()

    context = {
        'personal': personal,
        'contratos': contratos,
        'contrato_vigente': contrato_vigente,
        'timeline': timeline,
        'dias_restantes': dias_restantes,
        'estado_contrato': estado_contrato,
        'hoy': hoy,
    }
    return render(request, 'personal/contrato_detalle.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# EDITAR CONTRATO (legacy — campos en Personal)
# ═════════════════════════════════════════════════════════════════════════════

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
        return redirect('contrato_detalle', pk=personal.pk)

    context = {
        'personal': personal,
        'tipos': Personal.TIPO_CONTRATO_CHOICES,
    }
    return render(request, 'personal/contrato_editar.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# CREAR CONTRATO (modelo nuevo)
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contrato_crear(request, personal_pk):
    """Crea un nuevo contrato para un empleado usando el modelo Contrato."""
    personal = get_object_or_404(Personal, pk=personal_pk)

    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.personal = personal
            contrato.registrado_por = request.user
            contrato.save()
            # Sincronizar con Personal
            contrato.sincronizar_con_personal()
            messages.success(request, f"Contrato creado para {personal.apellidos_nombres}.")
            return redirect('contrato_detalle', pk=personal.pk)
    else:
        initial = {
            'tipo_contrato': personal.tipo_contrato,
            'fecha_inicio': personal.fecha_inicio_contrato,
            'fecha_fin': personal.fecha_fin_contrato,
            'sueldo_pactado': personal.sueldo_base,
            'cargo_contrato': personal.cargo,
            'renovacion_automatica': personal.renovacion_automatica,
        }
        form = ContratoForm(initial=initial)

    context = {
        'personal': personal,
        'form': form,
        'es_nuevo': True,
    }
    return render(request, 'personal/contrato_form.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# EDITAR CONTRATO (modelo nuevo)
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contrato_editar_obj(request, pk):
    """Edita un contrato del modelo Contrato."""
    contrato = get_object_or_404(Contrato, pk=pk)
    personal = contrato.personal

    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            form.save()
            if contrato.estado == 'VIGENTE':
                contrato.sincronizar_con_personal()
            messages.success(request, "Contrato actualizado.")
            return redirect('contrato_detalle', pk=personal.pk)
    else:
        form = ContratoForm(instance=contrato)

    context = {
        'personal': personal,
        'form': form,
        'contrato': contrato,
        'es_nuevo': False,
    }
    return render(request, 'personal/contrato_form.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# RENOVAR CONTRATO
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contrato_renovar(request, pk):
    """Renueva un contrato existente creando uno nuevo y vinculándolos."""
    contrato_original = get_object_or_404(Contrato, pk=pk)
    personal = contrato_original.personal

    if request.method == 'POST':
        form = RenovacionContratoForm(request.POST)
        if form.is_valid():
            # Marcar original como renovado
            contrato_original.estado = 'RENOVADO'
            contrato_original.save(update_fields=['estado'])

            # Crear nuevo contrato
            nuevo = Contrato.objects.create(
                personal=personal,
                tipo_contrato=form.cleaned_data['tipo_contrato'],
                fecha_inicio=form.cleaned_data['fecha_inicio'],
                fecha_fin=form.cleaned_data['fecha_fin'],
                sueldo_pactado=form.cleaned_data.get('sueldo_pactado') or contrato_original.sueldo_pactado,
                cargo_contrato=contrato_original.cargo_contrato,
                jornada_semanal=contrato_original.jornada_semanal,
                renovacion_automatica=contrato_original.renovacion_automatica,
                observaciones=form.cleaned_data.get('observaciones', ''),
                estado='VIGENTE',
                registrado_por=request.user,
            )

            # Registrar renovación
            RenovacionContrato.objects.create(
                contrato_original=contrato_original,
                contrato_nuevo=nuevo,
                fecha_renovacion=timezone.localdate(),
                motivo=form.cleaned_data.get('motivo', ''),
                registrado_por=request.user,
            )

            # Sincronizar con Personal
            nuevo.sincronizar_con_personal()

            messages.success(request, f"Contrato de {personal.apellidos_nombres} renovado exitosamente.")
            return redirect('contrato_detalle', pk=personal.pk)
    else:
        initial = {
            'tipo_contrato': contrato_original.tipo_contrato,
            'fecha_inicio': contrato_original.fecha_fin + relativedelta(days=1) if contrato_original.fecha_fin else timezone.localdate(),
            'sueldo_pactado': contrato_original.sueldo_pactado,
        }
        form = RenovacionContratoForm(initial=initial)

    context = {
        'personal': personal,
        'contrato_original': contrato_original,
        'form': form,
    }
    return render(request, 'personal/contrato_renovar.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# ADENDAS
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def adenda_crear(request, contrato_pk):
    """Crea una adenda para un contrato."""
    contrato = get_object_or_404(Contrato, pk=contrato_pk)
    personal = contrato.personal

    if request.method == 'POST':
        form = AdendaForm(request.POST, request.FILES)
        if form.is_valid():
            adenda = form.save(commit=False)
            adenda.contrato = contrato
            adenda.registrado_por = request.user
            adenda.save()
            messages.success(request, "Adenda registrada exitosamente.")
            return redirect('contrato_detalle', pk=personal.pk)
    else:
        form = AdendaForm(initial={'fecha': timezone.localdate()})

    context = {
        'personal': personal,
        'contrato': contrato,
        'form': form,
    }
    return render(request, 'personal/adenda_form.html', context)


# ═════════════════════════════════════════════════════════════════════════════
# EXPORTAR CONTRATOS A EXCEL
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contratos_exportar_excel(request):
    """Exporta la lista de contratos a Excel con filtros aplicados."""
    hoy = timezone.localdate()

    qs = Personal.objects.filter(estado='Activo').select_related('subarea__area').order_by('apellidos_nombres')

    # Aplicar mismos filtros que la lista
    buscar = request.GET.get('buscar', '').strip()
    tipo_f = request.GET.get('tipo', '')
    estado_f = request.GET.get('estado_contrato', '')
    area_f = request.GET.get('area', '')

    if buscar:
        qs = qs.filter(Q(apellidos_nombres__icontains=buscar) | Q(nro_doc__icontains=buscar))
    if tipo_f:
        qs = qs.filter(tipo_contrato=tipo_f)
    if area_f:
        qs = qs.filter(subarea__area_id=area_f)
    if estado_f == 'VIGENTE':
        qs = qs.filter(fecha_fin_contrato__gte=hoy)
    elif estado_f == 'VENCIDO':
        qs = qs.filter(fecha_fin_contrato__lt=hoy)
    elif estado_f == 'INDEFINIDO':
        qs = qs.filter(tipo_contrato='INDEFINIDO')
    elif estado_f == 'SIN_DATOS':
        qs = qs.filter(tipo_contrato='')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Contratos'

    # Título
    ws['A1'] = f'Reporte de Contratos Laborales — {hoy.strftime("%d/%m/%Y")}'
    ws['A1'].font = Font(size=13, bold=True, color='0D2B27')
    ws.merge_cells('A1:L1')
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.row_dimensions[1].height = 28

    # Headers
    headers = [
        'N°', 'Trabajador', 'DNI', 'Cargo', 'Área', 'SubÁrea',
        'Modalidad', 'Inicio', 'Vencimiento', 'Estado', 'Días Restantes',
        'Sueldo Base',
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = THIN_BORDER

    RED_FILL   = PatternFill("solid", fgColor="FEE2E2")
    AMBER_FILL = PatternFill("solid", fgColor="FEF3C7")
    GREEN_FILL = PatternFill("solid", fgColor="D1FAE5")

    for i, p in enumerate(qs, 1):
        row = i + 2
        dias = None
        estado = ''
        if p.fecha_fin_contrato:
            dias = (p.fecha_fin_contrato - hoy).days
            if dias < 0:
                estado = 'VENCIDO'
            elif dias <= 30:
                estado = 'URGENTE'
            else:
                estado = 'VIGENTE'
        elif p.tipo_contrato == 'INDEFINIDO':
            estado = 'INDEFINIDO'
        elif not p.tipo_contrato:
            estado = 'SIN DATOS'

        # Color urgencia
        if estado == 'VENCIDO':
            fill = RED_FILL
        elif estado == 'URGENTE':
            fill = AMBER_FILL
        elif estado == 'VIGENTE':
            fill = GREEN_FILL
        else:
            fill = ALT_FILL if i % 2 == 0 else PatternFill()

        area_n = p.subarea.area.nombre if p.subarea and p.subarea.area else '—'
        subarea_n = p.subarea.nombre if p.subarea else '—'

        values = [
            i,
            p.apellidos_nombres,
            p.nro_doc,
            p.cargo or '—',
            area_n,
            subarea_n,
            p.get_tipo_contrato_display() or '—',
            p.fecha_inicio_contrato,
            p.fecha_fin_contrato,
            estado,
            dias if dias is not None else '—',
            float(p.sueldo_base or 0),
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = fill
            cell.border = THIN_BORDER
            cell.alignment = Alignment(
                horizontal='center' if col in (1, 3, 8, 9, 10, 11) else 'left',
                vertical='center'
            )
            if col == 3:
                cell.number_format = '@'
            elif col == 12:
                cell.number_format = '"S/ "#,##0.00'

    # Auto-width
    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=10)
        from openpyxl.utils import get_column_letter
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 3, 50)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="contratos_{hoy.strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response


# ═════════════════════════════════════════════════════════════════════════════
# API: datos para dashboard de contratos (AJAX)
# ═════════════════════════════════════════════════════════════════════════════

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
        'vencen_60': activos.filter(
            fecha_fin_contrato__gte=hoy,
            fecha_fin_contrato__lte=hoy + relativedelta(days=60)
        ).count(),
        'vencen_90': activos.filter(
            fecha_fin_contrato__gte=hoy,
            fecha_fin_contrato__lte=hoy + relativedelta(days=90)
        ).count(),
        'vencidos': activos.filter(fecha_fin_contrato__lt=hoy).count(),
        'sin_contrato': activos.filter(tipo_contrato='').count(),
    })


# ═════════════════════════════════════════════════════════════════════════════
# ALERTAS DE CONTRATOS (widget para dashboard)
# ═════════════════════════════════════════════════════════════════════════════

@solo_admin
def contratos_alertas_json(request):
    """JSON con alertas de contratos por vencer para widgets del dashboard."""
    hoy = timezone.localdate()
    activos = Personal.objects.filter(estado='Activo')

    alertas = []

    # Contratos vencidos
    vencidos = activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__lt=hoy,
    ).select_related('subarea__area')
    for p in vencidos[:10]:
        dias = (hoy - p.fecha_fin_contrato).days
        alertas.append({
            'nivel': 'danger',
            'mensaje': f'{p.apellidos_nombres} — Contrato vencido hace {dias} día(s)',
            'personal_id': p.pk,
        })

    # Contratos por vencer en 30 días
    por_vencer = activos.filter(
        fecha_fin_contrato__gte=hoy,
        fecha_fin_contrato__lte=hoy + relativedelta(days=30),
    ).select_related('subarea__area').order_by('fecha_fin_contrato')
    for p in por_vencer[:10]:
        dias = (p.fecha_fin_contrato - hoy).days
        nivel = 'danger' if dias <= 7 else ('warning' if dias <= 15 else 'info')
        alertas.append({
            'nivel': nivel,
            'mensaje': f'{p.apellidos_nombres} — Contrato vence en {dias} día(s)',
            'personal_id': p.pk,
        })

    # Personal sin contrato
    sin_contrato_count = activos.filter(tipo_contrato='').count()
    if sin_contrato_count:
        alertas.append({
            'nivel': 'secondary',
            'mensaje': f'{sin_contrato_count} empleado(s) sin datos de contrato',
            'personal_id': None,
        })

    return JsonResponse({'alertas': alertas})
