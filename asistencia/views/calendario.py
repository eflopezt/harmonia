"""
Vista Calendario Grid — Asistencia diaria con justificación inline.
"""
import calendar
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from asistencia.models import RegistroTareo, HomologacionCodigo, CambioCodigoLog, FeriadoCalendario
from asistencia.views._common import solo_admin, _qs_staff_dedup
from personal.models import Personal, Area

# Códigos de presencia (días trabajados)
CODIGOS_PRESENCIA = {'T', 'NOR', 'TR', 'A', 'CDT', 'CPF', 'LCG', 'ATM', 'CHE', 'LIM', 'SS'}
CODIGOS_FALTA = {'F', 'FA', 'LSG'}
CODIGOS_DESCANSO = {'DL', 'DLA', 'DS'}
CODIGOS_VACACIONES = {'VAC', 'V'}
CODIGOS_MEDICO = {'DM', 'SUB'}

# Mapa de colores CSS por código
COLOR_MAP = {
    'NOR': 'present', 'T': 'present', 'A': 'present', 'TR': 'present',
    'SS': 'present',
    'F': 'falta', 'FA': 'falta',
    'VAC': 'vac', 'V': 'vac',
    'DL': 'descanso', 'DLA': 'descanso', 'DS': 'descanso',
    'DM': 'medico', 'SUB': 'medico',
    'CHE': 'comp', 'CDT': 'comp', 'CPF': 'comp',
    'LSG': 'lsg',
    'LCG': 'licencia', 'LF': 'licencia', 'LP': 'licencia',
    'FR': 'feriado', 'FER': 'feriado', 'FL': 'feriado',
    'LIM': 'lima', 'ATM': 'lima',
    'NA': 'empty',
}

MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
DIAS_SEMANA = ['L', 'M', 'Mi', 'J', 'V', 'S', 'D']


@login_required
@solo_admin
def calendario_grid(request):
    """Grilla calendario mensual de asistencia."""
    hoy = date.today()
    anio = int(request.GET.get('anio', hoy.year))
    mes = int(request.GET.get('mes', hoy.month))
    grupo = request.GET.get('grupo', 'TODOS')
    area_id = request.GET.get('area', '')
    condicion = request.GET.get('condicion', '')
    buscar = request.GET.get('q', '')

    _, num_dias = calendar.monthrange(anio, mes)
    mes_ini = date(anio, mes, 1)
    mes_fin = date(anio, mes, num_dias)

    # Días del mes con día de semana
    dias_mes = []
    for d in range(1, num_dias + 1):
        dt = date(anio, mes, d)
        dias_mes.append({
            'num': d,
            'dow': DIAS_SEMANA[dt.weekday()],
            'es_finde': dt.weekday() >= 5,
            'fecha': dt,
        })

    # Feriados
    feriados = set(
        FeriadoCalendario.objects
        .filter(fecha__gte=mes_ini, fecha__lte=mes_fin)
        .values_list('fecha', flat=True)
    )
    for d in dias_mes:
        d['es_feriado'] = d['fecha'] in feriados

    # Query registros
    if grupo == 'STAFF':
        qs = _qs_staff_dedup(mes_ini, mes_fin)
    elif grupo == 'RCO':
        qs = RegistroTareo.objects.filter(
            grupo='RCO', fecha__gte=mes_ini, fecha__lte=mes_fin,
            personal__isnull=False)
    else:
        # TODOS — combinar STAFF dedup + RCO
        qs_staff = _qs_staff_dedup(mes_ini, mes_fin)
        qs_rco = RegistroTareo.objects.filter(
            grupo='RCO', fecha__gte=mes_ini, fecha__lte=mes_fin,
            personal__isnull=False)
        qs = qs_staff | qs_rco

    # Filtros
    if area_id:
        qs = qs.filter(personal__subarea__area_id=area_id)
    if condicion:
        qs = qs.filter(condicion=condicion)
    if buscar:
        qs = qs.filter(
            Q(personal__apellidos_nombres__icontains=buscar) |
            Q(dni__icontains=buscar)
        )

    # Fetch all records
    registros = list(qs.select_related('personal').values(
        'id', 'personal_id', 'personal__apellidos_nombres', 'personal__nro_doc',
        'personal__condicion', 'personal__fecha_alta', 'personal__fecha_cese',
        'fecha', 'codigo_dia', 'grupo',
        'hora_entrada_real', 'hora_salida_real', 'horas_efectivas',
        'he_25', 'he_35', 'he_100', 'observaciones',
    ))

    # Pivot: personal_id -> {dia: registro}
    pivot = defaultdict(dict)
    personal_info = {}
    for r in registros:
        pid = r['personal_id']
        dia = r['fecha'].day
        pivot[pid][dia] = r
        if pid not in personal_info:
            personal_info[pid] = {
                'nombre': r['personal__apellidos_nombres'],
                'dni': r['personal__nro_doc'],
                'condicion': r['personal__condicion'] or '',
                'grupo': r['grupo'],
                'fecha_alta': r.get('personal__fecha_alta'),
                'fecha_cese': r.get('personal__fecha_cese'),
            }

    # Build rows sorted by name
    rows = []
    for pid in sorted(personal_info, key=lambda x: personal_info[x]['nombre']):
        info = personal_info[pid]
        celdas = []
        total_trab = 0
        total_falta = 0
        total_he = Decimal('0')
        fecha_alta = info.get('fecha_alta')
        fecha_cese = info.get('fecha_cese')
        for d in dias_mes:
            # N/A si fuera de periodo laboral
            if (fecha_alta and d['fecha'] < fecha_alta) or (fecha_cese and d['fecha'] > fecha_cese):
                celdas.append({'id': 0, 'codigo': 'NA', 'color': 'empty'})
                continue
            reg = pivot[pid].get(d['num'])
            if reg:
                codigo = reg['codigo_dia']
                # Auto DS para LOCAL domingos
                if d['fecha'].weekday() == 6 and info['condicion'].upper() in ('LOCAL', 'LIMA', '') and codigo in ('FA', 'F'):
                    codigo = 'DS'
                color = COLOR_MAP.get(codigo, 'other')
                if codigo in CODIGOS_PRESENCIA:
                    total_trab += 1
                elif codigo in CODIGOS_FALTA:
                    total_falta += 1
                he = (reg['he_25'] or 0) + (reg['he_35'] or 0) + (reg['he_100'] or 0)
                total_he += Decimal(str(he))
                celdas.append({
                    'id': reg['id'],
                    'codigo': codigo,
                    'color': color,
                    'entrada': str(reg['hora_entrada_real'])[:5] if reg['hora_entrada_real'] else '',
                    'salida': str(reg['hora_salida_real'])[:5] if reg['hora_salida_real'] else '',
                    'he': float(he) if he else 0,
                })
            else:
                auto_cod = ''
                if d['fecha'].weekday() == 6 and info['condicion'].upper() in ('LOCAL', 'LIMA', ''):
                    auto_cod = 'DS'
                celdas.append({'id': 0, 'codigo': auto_cod, 'color': COLOR_MAP.get(auto_cod, 'empty')})
        rows.append({
            'personal_id': pid,
            'nombre': info['nombre'],
            'dni': info['dni'],
            'condicion': info['condicion'],
            'grupo': info['grupo'],
            'celdas': celdas,
            'total_trab': total_trab,
            'total_falta': total_falta,
            'total_he': float(total_he),
        })

    # Summary per day
    resumen_dias = []
    for i, d in enumerate(dias_mes):
        presentes = sum(1 for r in rows if r['celdas'][i]['codigo'] in CODIGOS_PRESENCIA)
        ausentes = sum(1 for r in rows if r['celdas'][i]['codigo'] in CODIGOS_FALTA)
        total = presentes + ausentes
        pct = round(presentes / total * 100) if total else 0
        resumen_dias.append({'presentes': presentes, 'ausentes': ausentes, 'pct': pct})

    # Stats globales
    total_presentes = sum(r['total_trab'] for r in rows)
    total_faltas = sum(r['total_falta'] for r in rows)
    total_registros = total_presentes + total_faltas
    pct_global = round(total_presentes / total_registros * 100, 1) if total_registros else 0

    # Areas para filtro
    areas = Area.objects.all().order_by('nombre')

    # Códigos disponibles para justificación
    codigos_disponibles = list(
        HomologacionCodigo.objects
        .filter(activo=True)
        .values('codigo', 'descripcion')
        .order_by('codigo')
    )

    context = {
        'titulo': f'Calendario de Asistencia — {MESES[mes]} {anio}',
        'anio': anio, 'mes': mes, 'mes_nombre': MESES[mes],
        'dias_mes': dias_mes, 'num_dias': num_dias,
        'rows': rows, 'resumen_dias': resumen_dias,
        'total_empleados': len(rows),
        'total_presentes': total_presentes,
        'total_faltas': total_faltas,
        'pct_global': pct_global,
        'grupo': grupo, 'area_id': area_id, 'condicion': condicion, 'buscar': buscar,
        'areas': areas,
        'codigos_json': json.dumps(codigos_disponibles),
        'color_map_json': json.dumps(COLOR_MAP),
        'anios': list(range(hoy.year - 2, hoy.year + 1)),
        'meses_list': [(i, MESES[i]) for i in range(1, 13)],
    }
    return render(request, 'asistencia/calendario_grid.html', context)


@login_required
@solo_admin
def ajax_calendario_detalle(request, registro_id):
    """Detalle de celda para el modal."""
    reg = get_object_or_404(
        RegistroTareo.objects.select_related('personal'),
        pk=registro_id
    )
    cambios = list(
        CambioCodigoLog.objects
        .filter(registro=reg)
        .select_related('usuario')
        .values('codigo_anterior', 'codigo_nuevo', 'observacion', 'creado_en', 'usuario__username')
        .order_by('-creado_en')[:10]
    )
    for c in cambios:
        c['creado_en'] = c['creado_en'].strftime('%d/%m/%Y %H:%M')

    data = {
        'id': reg.id,
        'nombre': reg.personal.apellidos_nombres if reg.personal else reg.dni,
        'dni': reg.dni,
        'fecha': reg.fecha.strftime('%d/%m/%Y'),
        'fecha_dow': DIAS_SEMANA[reg.fecha.weekday()],
        'codigo': reg.codigo_dia,
        'color': COLOR_MAP.get(reg.codigo_dia, 'other'),
        'grupo': reg.grupo,
        'condicion': reg.condicion,
        'entrada': str(reg.hora_entrada_real)[:5] if reg.hora_entrada_real else '-',
        'salida': str(reg.hora_salida_real)[:5] if reg.hora_salida_real else '-',
        'horas_efectivas': float(reg.horas_efectivas or 0),
        'horas_normales': float(reg.horas_normales or 0),
        'he_25': float(reg.he_25 or 0),
        'he_35': float(reg.he_35 or 0),
        'he_100': float(reg.he_100 or 0),
        'observaciones': reg.observaciones or '',
        'fuente': reg.fuente_codigo,
        'cambios': cambios,
    }
    return JsonResponse(data)


@login_required
@solo_admin
@require_POST
def ajax_calendario_cambiar(request, registro_id):
    """Cambiar código de un registro (justificación)."""
    reg = get_object_or_404(RegistroTareo, pk=registro_id)
    nuevo_codigo = request.POST.get('codigo', '').strip().upper()
    observacion = request.POST.get('observacion', '').strip()
    sustento = request.FILES.get('sustento')

    if not nuevo_codigo:
        return JsonResponse({'error': 'Código requerido'}, status=400)

    codigo_anterior = reg.codigo_dia

    # Log del cambio
    log = CambioCodigoLog.objects.create(
        registro=reg,
        codigo_anterior=codigo_anterior,
        codigo_nuevo=nuevo_codigo,
        observacion=observacion,
        sustento=sustento,
        usuario=request.user,
    )

    # Actualizar registro
    reg.codigo_dia = nuevo_codigo
    reg.fuente_codigo = 'MANUAL'
    if observacion:
        prev = reg.observaciones or ''
        reg.observaciones = f'{prev}\n[{request.user.username}] {codigo_anterior}→{nuevo_codigo}: {observacion}'.strip()
    reg.save()

    return JsonResponse({
        'ok': True,
        'codigo': nuevo_codigo,
        'color': COLOR_MAP.get(nuevo_codigo, 'other'),
        'anterior': codigo_anterior,
    })


@login_required
@solo_admin
def calendario_exportar(request):
    """Exportar calendario a Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from io import BytesIO

    anio = int(request.GET.get('anio', date.today().year))
    mes = int(request.GET.get('mes', date.today().month))
    grupo = request.GET.get('grupo', 'TODOS')

    _, num_dias = calendar.monthrange(anio, mes)
    mes_ini = date(anio, mes, 1)
    mes_fin = date(anio, mes, num_dias)

    # Query
    if grupo == 'STAFF':
        qs = _qs_staff_dedup(mes_ini, mes_fin)
    elif grupo == 'RCO':
        qs = RegistroTareo.objects.filter(grupo='RCO', fecha__gte=mes_ini, fecha__lte=mes_fin, personal__isnull=False)
    else:
        qs = _qs_staff_dedup(mes_ini, mes_fin) | RegistroTareo.objects.filter(
            grupo='RCO', fecha__gte=mes_ini, fecha__lte=mes_fin, personal__isnull=False)

    registros = list(qs.select_related('personal').values(
        'personal_id', 'personal__apellidos_nombres', 'personal__nro_doc',
        'personal__condicion', 'fecha', 'codigo_dia', 'grupo'))

    pivot = defaultdict(dict)
    personal_info = {}
    for r in registros:
        pid = r['personal_id']
        pivot[pid][r['fecha'].day] = r['codigo_dia']
        if pid not in personal_info:
            personal_info[pid] = {
                'nombre': r['personal__apellidos_nombres'],
                'dni': r['personal__nro_doc'],
                'condicion': r['personal__condicion'] or '',
                'grupo': r['grupo'],
                'fecha_alta': r.get('personal__fecha_alta'),
                'fecha_cese': r.get('personal__fecha_cese'),
            }

    # Colors
    FILLS = {
        'present': PatternFill(start_color='D1FAE5', end_color='D1FAE5', fill_type='solid'),
        'falta': PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid'),
        'vac': PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid'),
        'descanso': PatternFill(start_color='E5E7EB', end_color='E5E7EB', fill_type='solid'),
        'medico': PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid'),
        'comp': PatternFill(start_color='FFEDD5', end_color='FFEDD5', fill_type='solid'),
        'lsg': PatternFill(start_color='EDE9FE', end_color='EDE9FE', fill_type='solid'),
        'licencia': PatternFill(start_color='CFFAFE', end_color='CFFAFE', fill_type='solid'),
    }
    header_fill = PatternFill(start_color='1A2B47', end_color='1A2B47', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=9)
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB'),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = f'{MESES[mes]} {anio}'

    # Header
    headers = ['N°', 'DNI', 'Empleado', 'Cond.', 'Grupo']
    for d in range(1, num_dias + 1):
        dt = date(anio, mes, d)
        headers.append(f'{d}\n{DIAS_SEMANA[dt.weekday()]}')
    headers.extend(['Trab', 'Falta', 'HE'])

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    # Data rows
    row_num = 2
    for idx, pid in enumerate(sorted(personal_info, key=lambda x: personal_info[x]['nombre']), 1):
        info = personal_info[pid]
        ws.cell(row=row_num, column=1, value=idx).border = thin_border
        ws.cell(row=row_num, column=2, value=info['dni']).border = thin_border
        ws.cell(row=row_num, column=3, value=info['nombre']).border = thin_border
        ws.cell(row=row_num, column=4, value=info['condicion']).border = thin_border
        ws.cell(row=row_num, column=5, value=info['grupo']).border = thin_border

        trab = falta = 0
        for d in range(1, num_dias + 1):
            codigo = pivot[pid].get(d, '')
            col = 5 + d
            cell = ws.cell(row=row_num, column=col, value=codigo)
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
            cell.font = Font(size=8, bold=True)
            color_key = COLOR_MAP.get(codigo, '')
            if color_key in FILLS:
                cell.fill = FILLS[color_key]
            if codigo in CODIGOS_PRESENCIA:
                trab += 1
            elif codigo in CODIGOS_FALTA:
                falta += 1

        ws.cell(row=row_num, column=5 + num_dias + 1, value=trab).border = thin_border
        ws.cell(row=row_num, column=5 + num_dias + 2, value=falta).border = thin_border
        row_num += 1

    # Column widths
    ws.column_dimensions['A'].width = 4
    ws.column_dimensions['B'].width = 11
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 8
    ws.column_dimensions['E'].width = 7
    for d in range(1, num_dias + 1):
        col_letter = ws.cell(row=1, column=5 + d).column_letter
        ws.column_dimensions[col_letter].width = 4.5

    ws.freeze_panes = 'F2'

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=calendario_{MESES[mes]}_{anio}.xlsx'
    return response
