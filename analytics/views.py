"""
Analytics & People Intelligence — Vistas.

Dashboard ejecutivo con KPIs en tiempo real y tendencias históricas.
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages

from .models import KPISnapshot, AlertaRRHH
from .services import generar_snapshot, generar_alertas

solo_admin = user_passes_test(lambda u: u.is_superuser, login_url='login')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder que maneja Decimal."""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


# ─────────────────────────────────────────────────
# DASHBOARD EJECUTIVO
# ─────────────────────────────────────────────────

@solo_admin
def dashboard(request):
    """Dashboard ejecutivo de RRHH con KPIs y tendencias."""
    from personal.models import Personal, Area

    # ── KPI en tiempo real ──
    activos = Personal.objects.filter(estado='Activo')
    total = activos.count()
    staff = activos.filter(grupo_tareo='STAFF').count()
    rco = activos.filter(grupo_tareo='RCO').count()

    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)

    altas_mes = Personal.objects.filter(
        fecha_alta__gte=inicio_mes, fecha_alta__lte=hoy).count()
    bajas_mes = Personal.objects.filter(
        fecha_cese__gte=inicio_mes, fecha_cese__lte=hoy, estado='Cesado').count()

    # ── Distribución por área ──
    areas_data = (
        activos
        .values('subarea__area__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    areas_labels = [a['subarea__area__nombre'] or 'Sin Área' for a in areas_data]
    areas_values = [a['total'] for a in areas_data]

    # ── Tendencia histórica (últimos 12 meses) ──
    snapshots = KPISnapshot.objects.order_by('-periodo')[:12][::-1]
    trend_labels = [s.periodo.strftime('%b %Y') for s in snapshots]
    trend_headcount = [s.total_empleados for s in snapshots]
    trend_staff = [s.empleados_staff for s in snapshots]
    trend_rco = [s.empleados_rco for s in snapshots]
    trend_rotacion = [float(s.tasa_rotacion) for s in snapshots]
    trend_asistencia = [float(s.tasa_asistencia) for s in snapshots]
    trend_he = [float(s.total_he_mes) for s in snapshots]

    # ── Si no hay snapshots, build live 6-month trend ──
    if not snapshots:
        live_labels = []
        live_hc = []
        for i in range(5, -1, -1):
            ref = date(hoy.year, hoy.month, 1) - timedelta(days=i * 30)
            mes_label = ref.strftime('%b %Y')
            count = Personal.objects.filter(
                fecha_alta__lte=ref
            ).exclude(
                fecha_cese__lt=ref
            ).count()
            live_labels.append(mes_label)
            live_hc.append(count)
        trend_labels = live_labels
        trend_headcount = live_hc
        trend_staff = []
        trend_rco = []
        trend_rotacion = []
        trend_asistencia = []
        trend_he = []

    # ── Alertas activas (últimas 5 para widget) ──
    alertas = AlertaRRHH.objects.filter(estado='ACTIVA').order_by('-creado_en')[:5]
    total_alertas_activas = AlertaRRHH.objects.filter(estado='ACTIVA').count()

    # ── Snapshots: actual y anterior para deltas ──
    snapshots_recientes = KPISnapshot.objects.order_by('-periodo')[:2]
    ultimo_snapshot = snapshots_recientes[0] if snapshots_recientes else None
    penultimo_snapshot = snapshots_recientes[1] if len(snapshots_recientes) > 1 else None

    # ── Tasa asistencia actual (mes en curso) ──
    tasa_asistencia_actual = None
    try:
        from asistencia.models import RegistroTareo
        registros_mes = RegistroTareo.objects.filter(
            fecha__gte=inicio_mes, fecha__lte=hoy)
        total_reg = registros_mes.count()
        asistidos = registros_mes.exclude(
            codigo_dia__in=['F', 'FALTA', 'SIN_MARCACION', 'FERIADO']).count()
        if total_reg > 0:
            tasa_asistencia_actual = round(asistidos / total_reg * 100, 1)
    except Exception:
        pass

    # ── People Risk summary ──
    hoy_60 = hoy + timedelta(days=60)
    contratos_vencen = Personal.objects.filter(
        estado='Activo',
        tipo_contrato='PLAZO_FIJO',
        fecha_fin_contrato__gte=hoy,
        fecha_fin_contrato__lte=hoy_60,
    ).count()

    # Ausentismo crítico (faltas > 3 en el mes): best-effort
    ausentismo_critico = 0
    try:
        from asistencia.models import RegistroTareo
        from django.db.models import Count as DjCount
        faltas_por_persona = (
            RegistroTareo.objects.filter(
                fecha__gte=inicio_mes,
                fecha__lte=hoy,
                codigo_dia__in=['F', 'FALTA'],
            )
            .values('personal_id')
            .annotate(faltas=DjCount('id'))
            .filter(faltas__gt=3)
        )
        ausentismo_critico = faltas_por_persona.count()
    except Exception:
        pass

    # High risk count (simplified for widget — full calc in attrition_risk view)
    riesgo_alto = 0
    try:
        riesgo_alto = Personal.objects.filter(
            estado='Activo',
            tipo_contrato='PLAZO_FIJO',
            fecha_fin_contrato__gte=hoy,
            fecha_fin_contrato__lte=hoy_60,
        ).count()
    except Exception:
        pass

    # ── Alertas activas enriquecidas (top 5, por severidad desc luego fecha desc) ──
    # Orden manual: CRITICAL > WARN > INFO usando Case/When
    top_alertas = []
    try:
        from django.db.models import Case, IntegerField, When
        top_alertas = list(
            AlertaRRHH.objects.filter(estado='ACTIVA').annotate(
                sev_order=Case(
                    When(severidad='CRITICAL', then=0),
                    When(severidad='WARN', then=1),
                    When(severidad='INFO', then=2),
                    default=3,
                    output_field=IntegerField(),
                )
            ).order_by('sev_order', '-creado_en')[:5]
        )
    except Exception:
        pass

    # ── Módulos resumen (señales por módulo) ──
    modulos_resumen = []

    # Vacaciones pendientes
    try:
        from vacaciones.models import SolicitudVacacion
        vac_count = SolicitudVacacion.objects.filter(estado='PENDIENTE').count()
    except Exception:
        vac_count = 0
    modulos_resumen.append({
        'label': 'Vacaciones pendientes',
        'value': vac_count,
        'icon': 'fas fa-umbrella-beach',
        'color': '#0891b2',
        'url': 'vacaciones_panel',
    })

    # Permisos pendientes
    try:
        from vacaciones.models import SolicitudPermiso
        per_count = SolicitudPermiso.objects.filter(estado='PENDIENTE').count()
    except Exception:
        per_count = 0
    modulos_resumen.append({
        'label': 'Permisos pendientes',
        'value': per_count,
        'icon': 'fas fa-file-alt',
        'color': '#7c3aed',
        'url': 'permisos_panel',
    })

    # Préstamos activos
    try:
        from prestamos.models import Prestamo
        pre_count = Prestamo.objects.filter(estado='EN_CURSO').count()
    except Exception:
        pre_count = 0
    modulos_resumen.append({
        'label': 'Préstamos activos',
        'value': pre_count,
        'icon': 'fas fa-hand-holding-usd',
        'color': '#d97706',
        'url': 'prestamos_panel',
    })

    # Capacitaciones en curso
    try:
        from capacitaciones.models import Capacitacion
        cap_count = Capacitacion.objects.filter(estado='EN_CURSO').count()
    except Exception:
        cap_count = 0
    modulos_resumen.append({
        'label': 'Capacitaciones en curso',
        'value': cap_count,
        'icon': 'fas fa-chalkboard-teacher',
        'color': '#059669',
        'url': 'capacitaciones_panel',
    })

    # Evaluaciones pendientes
    try:
        from evaluaciones.models import Evaluacion
        eva_count = Evaluacion.objects.filter(estado='PENDIENTE').count()
    except Exception:
        eva_count = 0
    modulos_resumen.append({
        'label': 'Evaluaciones pendientes',
        'value': eva_count,
        'icon': 'fas fa-star-half-alt',
        'color': '#db2777',
        'url': 'evaluaciones_dashboard',
    })

    # Vacantes abiertas
    try:
        from reclutamiento.models import Vacante
        vac_open_count = Vacante.objects.filter(estado='PUBLICADA').count()
    except Exception:
        vac_open_count = 0
    modulos_resumen.append({
        'label': 'Vacantes abiertas',
        'value': vac_open_count,
        'icon': 'fas fa-briefcase',
        'color': '#2563eb',
        'url': 'reclutamiento_dashboard',
    })

    # ── Próximos cumpleaños (personal activo, próximos 30 días) ──
    proximos_cumpleanios = []
    try:
        from django.db.models.functions import ExtractMonth, ExtractDay
        hoy_30 = hoy + timedelta(days=30)
        activos_con_nacimiento = Personal.objects.filter(
            estado='Activo',
            fecha_nacimiento__isnull=False,
        )
        candidatos = []
        for p in activos_con_nacimiento.only('apellidos_nombres', 'fecha_nacimiento'):
            fn = p.fecha_nacimiento
            # Calcular próximo cumpleaños en el año actual o siguiente
            try:
                proximo = fn.replace(year=hoy.year)
            except ValueError:
                # 29 Feb en año no bisiesto
                proximo = fn.replace(year=hoy.year, day=28)
            if proximo < hoy:
                try:
                    proximo = fn.replace(year=hoy.year + 1)
                except ValueError:
                    proximo = fn.replace(year=hoy.year + 1, day=28)
            dias = (proximo - hoy).days
            if 0 <= dias <= 30:
                candidatos.append({
                    'nombre': p.apellidos_nombres,
                    'fecha_cumple': proximo,
                    'dias_para_cumple': dias,
                })
        candidatos.sort(key=lambda x: x['dias_para_cumple'])
        proximos_cumpleanios = candidatos[:5]
    except Exception:
        pass

    context = {
        'total_empleados': total,
        'empleados_staff': staff,
        'empleados_rco': rco,
        'altas_mes': altas_mes,
        'bajas_mes': bajas_mes,
        'areas_labels': json.dumps(areas_labels),
        'areas_values': json.dumps(areas_values),
        'trend_labels': json.dumps(trend_labels),
        'trend_headcount': json.dumps(trend_headcount),
        'trend_staff': json.dumps(trend_staff),
        'trend_rco': json.dumps(trend_rco),
        'trend_rotacion': json.dumps(trend_rotacion),
        'trend_asistencia': json.dumps(trend_asistencia),
        'trend_he': json.dumps(trend_he, cls=DecimalEncoder),
        'alertas': alertas,
        'total_alertas_activas': total_alertas_activas,
        'ultimo_snapshot': ultimo_snapshot,
        'penultimo_snapshot': penultimo_snapshot,
        'tasa_asistencia_actual': tasa_asistencia_actual,
        'total_areas': len(areas_labels),
        # People Risk
        'riesgo_alto': riesgo_alto,
        'contratos_vencen': contratos_vencen,
        'ausentismo_critico': ausentismo_critico,
        # Nuevas señales por módulo y alertas enriquecidas
        'top_alertas': top_alertas,
        'modulos_resumen': modulos_resumen,
        'proximos_cumpleanios': proximos_cumpleanios,
    }
    return render(request, 'analytics/dashboard.html', context)


# ─────────────────────────────────────────────────
# HEADCOUNT DETALLADO
# ─────────────────────────────────────────────────

@solo_admin
def headcount(request):
    """Vista detallada de headcount con pirámide, tendencia y género."""
    from personal.models import Personal, Area

    activos = Personal.objects.filter(estado='Activo')
    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)

    # ── Por área y tipo ──
    areas = Area.objects.filter(activa=True).order_by('nombre')
    total = activos.count()
    area_data = []
    for area in areas:
        staff = activos.filter(subarea__area=area, grupo_tareo='STAFF').count()
        rco = activos.filter(subarea__area=area, grupo_tareo='RCO').count()
        if staff + rco > 0:
            area_data.append({
                'nombre': area.nombre,
                'staff': staff,
                'rco': rco,
                'total': staff + rco,
            })

    # ── Antigüedad ──
    antiguedad = {
        'menos_1': activos.filter(fecha_alta__gte=hoy - timedelta(days=365)).count(),
        '1_3': activos.filter(
            fecha_alta__lt=hoy - timedelta(days=365),
            fecha_alta__gte=hoy - timedelta(days=365 * 3)
        ).count(),
        '3_5': activos.filter(
            fecha_alta__lt=hoy - timedelta(days=365 * 3),
            fecha_alta__gte=hoy - timedelta(days=365 * 5)
        ).count(),
        'mas_5': activos.filter(fecha_alta__lt=hoy - timedelta(days=365 * 5)).count(),
    }

    # ── Distribución por género ──
    genero_m = activos.filter(sexo='M').count()
    genero_f = activos.filter(sexo='F').count()
    genero_nd = total - genero_m - genero_f

    # ── Tendencia mensual últimos 12 meses (live query) ──
    monthly_labels = []
    monthly_hc = []
    monthly_staff = []
    monthly_rco = []
    altas_list = []
    bajas_list = []

    for i in range(11, -1, -1):
        # Primer día del mes i meses atrás
        ref_month = date(hoy.year, hoy.month, 1) - timedelta(days=i * 30)
        ref_month = date(ref_month.year, ref_month.month, 1)
        # Último día de ese mes
        if ref_month.month == 12:
            next_month = date(ref_month.year + 1, 1, 1)
        else:
            next_month = date(ref_month.year, ref_month.month + 1, 1)
        last_day = next_month - timedelta(days=1)

        hc = Personal.objects.filter(
            fecha_alta__lte=last_day
        ).exclude(
            fecha_cese__lt=ref_month
        ).count()
        st = Personal.objects.filter(
            fecha_alta__lte=last_day,
            grupo_tareo='STAFF'
        ).exclude(
            fecha_cese__lt=ref_month
        ).count()
        rc = Personal.objects.filter(
            fecha_alta__lte=last_day,
            grupo_tareo='RCO'
        ).exclude(
            fecha_cese__lt=ref_month
        ).count()
        altas = Personal.objects.filter(
            fecha_alta__gte=ref_month,
            fecha_alta__lte=last_day
        ).count()
        bajas = Personal.objects.filter(
            fecha_cese__gte=ref_month,
            fecha_cese__lte=last_day,
            estado='Cesado'
        ).count()

        monthly_labels.append(ref_month.strftime('%b %Y'))
        monthly_hc.append(hc)
        monthly_staff.append(st)
        monthly_rco.append(rc)
        altas_list.append(altas)
        bajas_list.append(bajas)

    # ── Tasa de Rotación últimos 12 meses ──
    total_altas_12 = sum(altas_list)
    total_bajas_12 = sum(bajas_list)
    promedio_hc = sum(monthly_hc) / len(monthly_hc) if monthly_hc else 1
    tasa_rotacion_anual = round((total_altas_12 + total_bajas_12) / (promedio_hc * 2) * 100, 1) if promedio_hc else 0

    # ── Pirámide de edad (si hay fechas) ──
    piramide_labels = ['<25', '25-34', '35-44', '45-54', '55+']
    piramide_m = [0, 0, 0, 0, 0]
    piramide_f = [0, 0, 0, 0, 0]
    edad_bins = [(0, 24), (25, 34), (35, 44), (45, 54), (55, 999)]
    for idx, (min_age, max_age) in enumerate(edad_bins):
        min_date = hoy - timedelta(days=max_age * 365 + 365)
        max_date = hoy - timedelta(days=min_age * 365)
        qs = activos.filter(fecha_nacimiento__isnull=False,
                            fecha_nacimiento__gte=min_date,
                            fecha_nacimiento__lte=max_date)
        piramide_m[idx] = qs.filter(sexo='M').count()
        piramide_f[idx] = qs.filter(sexo='F').count()

    tiene_edad = any(piramide_m) or any(piramide_f)

    context = {
        'area_data': area_data,
        'total': total,
        'antiguedad': antiguedad,
        'antiguedad_json': json.dumps(antiguedad),
        # Género
        'genero_m': genero_m,
        'genero_f': genero_f,
        'genero_nd': genero_nd,
        # Tendencia
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_hc': json.dumps(monthly_hc),
        'monthly_staff': json.dumps(monthly_staff),
        'monthly_rco': json.dumps(monthly_rco),
        'altas_list': json.dumps(altas_list),
        'bajas_list': json.dumps(bajas_list),
        # Rotación
        'tasa_rotacion_anual': tasa_rotacion_anual,
        'total_altas_12': total_altas_12,
        'total_bajas_12': total_bajas_12,
        # Pirámide
        'piramide_labels': json.dumps(piramide_labels),
        'piramide_m': json.dumps(piramide_m),
        'piramide_f': json.dumps(piramide_f),
        'tiene_edad': tiene_edad,
    }
    return render(request, 'analytics/headcount.html', context)


# ─────────────────────────────────────────────────
# RIESGO DE ROTACIÓN (ATTRITION RISK)
# ─────────────────────────────────────────────────

@solo_admin
def attrition_risk(request):
    """
    Vista de riesgo de rotación por empleado.
    Scoring basado en reglas: contrato, faltas, sueldo, evaluaciones, capacitaciones.
    """
    from personal.models import Personal

    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)
    hace_6m = hoy - timedelta(days=180)
    hace_1y = hoy - timedelta(days=365)
    en_60d = hoy + timedelta(days=60)

    activos = Personal.objects.filter(estado='Activo').select_related('subarea', 'subarea__area')

    # ── Precalcular datos para scoring ──

    # Faltas por persona en el último mes
    faltas_por_persona = {}
    try:
        from asistencia.models import RegistroTareo
        faltas_qs = (
            RegistroTareo.objects.filter(
                fecha__gte=inicio_mes,
                fecha__lte=hoy,
                codigo_dia__in=['F', 'FALTA'],
                personal__isnull=False,
            )
            .values('personal_id')
            .annotate(n=Count('id'))
        )
        for row in faltas_qs:
            faltas_por_persona[row['personal_id']] = row['n']
    except Exception:
        pass

    # Empleados con evaluación reciente (últimos 6 meses)
    con_evaluacion = set()
    try:
        from evaluaciones.models import ResultadoConsolidado
        evals = ResultadoConsolidado.objects.filter(
            fecha_consolidacion__gte=hace_6m
        ).values_list('personal_id', flat=True)
        con_evaluacion = set(evals)
    except Exception:
        pass

    # Empleados con capacitación reciente (último año)
    con_capacitacion = set()
    try:
        from capacitaciones.models import AsistenciaCapacitacion
        caps = AsistenciaCapacitacion.objects.filter(
            capacitacion__fecha_inicio__gte=hace_1y,
            asistio=True,
        ).values_list('personal_id', flat=True)
        con_capacitacion = set(caps)
    except Exception:
        pass

    # Bandas salariales mínimas por cargo
    bandas_min = {}
    try:
        from salarios.models import BandaSalarial
        for banda in BandaSalarial.objects.filter(activa=True):
            cargo_key = banda.cargo.strip().lower()
            if cargo_key not in bandas_min or banda.minimo < bandas_min[cargo_key]:
                bandas_min[cargo_key] = float(banda.minimo)
    except Exception:
        pass

    # ── Scoring ──
    results = []
    for emp in activos:
        score = 0
        factores = []

        # +30 si contrato plazo fijo vence en 60 días
        if (emp.tipo_contrato == 'PLAZO_FIJO' and
                emp.fecha_fin_contrato and
                hoy <= emp.fecha_fin_contrato <= en_60d):
            score += 30
            dias_restantes = (emp.fecha_fin_contrato - hoy).days
            factores.append(f'Contrato vence en {dias_restantes}d')

        # +20 si faltas > 3 en el último mes
        faltas = faltas_por_persona.get(emp.id, 0)
        if faltas > 3:
            score += 20
            factores.append(f'{faltas} faltas/mes')

        # +15 si sueldo < mínimo de banda de su cargo
        if emp.sueldo_base and emp.cargo:
            cargo_key = emp.cargo.strip().lower()
            banda_min = bandas_min.get(cargo_key)
            if banda_min and float(emp.sueldo_base) < banda_min:
                score += 15
                factores.append('Sueldo bajo banda')

        # +10 si no tiene evaluación en últimos 6 meses
        if emp.id not in con_evaluacion:
            score += 10
            factores.append('Sin evaluación reciente')

        # +10 si no tiene capacitación en el último año
        if emp.id not in con_capacitacion:
            score += 10
            factores.append('Sin capacitación')

        # Nivel de riesgo
        if score >= 40:
            nivel = 'HIGH'
        elif score >= 20:
            nivel = 'MEDIUM'
        else:
            nivel = 'LOW'

        results.append({
            'emp': emp,
            'score': score,
            'nivel': nivel,
            'factores': factores,
            'area': emp.subarea.area.nombre if emp.subarea and emp.subarea.area else 'Sin área',
        })

    # Ordenar: HIGH primero, luego score desc
    level_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    results.sort(key=lambda x: (level_order[x['nivel']], -x['score']))

    # Conteos por nivel
    count_high = sum(1 for r in results if r['nivel'] == 'HIGH')
    count_medium = sum(1 for r in results if r['nivel'] == 'MEDIUM')
    count_low = sum(1 for r in results if r['nivel'] == 'LOW')

    # Top 10 para gráfico horizontal
    top10 = results[:10]
    chart_labels = [r['emp'].apellidos_nombres for r in top10]
    chart_scores = [r['score'] for r in top10]
    chart_colors = [
        '#dc2626' if r['nivel'] == 'HIGH' else
        '#f59e0b' if r['nivel'] == 'MEDIUM' else '#16a34a'
        for r in top10
    ]

    context = {
        'results': results,
        'count_high': count_high,
        'count_medium': count_medium,
        'count_low': count_low,
        'total': len(results),
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores),
        'chart_colors': json.dumps(chart_colors),
    }
    return render(request, 'analytics/attrition_risk.html', context)


# ─────────────────────────────────────────────────
# ANÁLISIS SALARIAL
# ─────────────────────────────────────────────────

@solo_admin
def salary_analytics(request):
    """Vista de análisis salarial: distribución, brechas, percentiles."""
    from personal.models import Personal, Area

    UIT_2026 = Decimal('5350.00')

    activos_con_sueldo = (
        Personal.objects.filter(estado='Activo', sueldo_base__isnull=False)
        .select_related('subarea', 'subarea__area')
    )

    sueldos = list(activos_con_sueldo.values_list('sueldo_base', flat=True))
    sueldos_float = sorted([float(s) for s in sueldos])
    n = len(sueldos_float)

    # ── KPIs básicos ──
    total_planilla = sum(sueldos_float)
    promedio = total_planilla / n if n else 0
    mediana = sueldos_float[n // 2] if n else 0

    # ── Brecha de género ──
    avg_m = activos_con_sueldo.filter(sexo='M').aggregate(avg=Avg('sueldo_base'))['avg'] or 0
    avg_f = activos_con_sueldo.filter(sexo='F').aggregate(avg=Avg('sueldo_base'))['avg'] or 0
    gap_pct = 0
    if avg_m and avg_f and avg_m > 0:
        gap_pct = round(float((avg_m - avg_f) / avg_m) * 100, 1)

    # ── Distribución por rango (bins) ──
    bins = [
        ('Menos de S/2,000', 0, 2000),
        ('S/2,000 – 3,000', 2000, 3000),
        ('S/3,000 – 5,000', 3000, 5000),
        ('S/5,000 – 8,000', 5000, 8000),
        ('Más de S/8,000', 8000, 99999999),
    ]
    dist_labels = []
    dist_values = []
    for label, lo, hi in bins:
        count = activos_con_sueldo.filter(
            sueldo_base__gte=lo, sueldo_base__lt=hi
        ).count()
        dist_labels.append(label)
        dist_values.append(count)

    # ── Promedio por área ──
    area_avg_qs = (
        activos_con_sueldo
        .values('subarea__area__nombre')
        .annotate(avg=Avg('sueldo_base'), cnt=Count('id'))
        .order_by('-avg')
    )
    area_labels = [r['subarea__area__nombre'] or 'Sin Área' for r in area_avg_qs]
    area_avg_values = [round(float(r['avg']), 2) for r in area_avg_qs]

    # ── Percentiles ──
    def percentil(lst, p):
        if not lst:
            return 0
        idx = int(len(lst) * p / 100)
        idx = min(idx, len(lst) - 1)
        return lst[idx]

    p25 = percentil(sueldos_float, 25)
    p50 = percentil(sueldos_float, 50)
    p75 = percentil(sueldos_float, 75)
    p90 = percentil(sueldos_float, 90)

    # ── Ratio vs UIT ──
    ratio_bins = [
        ('< 1 UIT', 0, float(UIT_2026)),
        ('1 – 2 UIT', float(UIT_2026), float(UIT_2026 * 2)),
        ('2 – 3 UIT', float(UIT_2026 * 2), float(UIT_2026 * 3)),
        ('> 3 UIT', float(UIT_2026 * 3), 99999999),
    ]
    uit_labels = []
    uit_values = []
    for label, lo, hi in ratio_bins:
        count = activos_con_sueldo.filter(
            sueldo_base__gte=lo, sueldo_base__lt=hi
        ).count()
        uit_labels.append(label)
        uit_values.append(count)

    # ── Top 5 / Bottom 5 sueldos (para tabla, no nombres) ──
    top5 = list(activos_con_sueldo.order_by('-sueldo_base')[:5].values(
        'apellidos_nombres', 'cargo', 'sueldo_base', 'subarea__area__nombre'
    ))
    bottom5 = list(activos_con_sueldo.order_by('sueldo_base')[:5].values(
        'apellidos_nombres', 'cargo', 'sueldo_base', 'subarea__area__nombre'
    ))

    context = {
        'n_empleados': n,
        'total_planilla': round(total_planilla, 2),
        'promedio': round(promedio, 2),
        'mediana': round(mediana, 2),
        'avg_m': round(float(avg_m), 2),
        'avg_f': round(float(avg_f), 2),
        'gap_pct': gap_pct,
        'p25': round(p25, 2),
        'p50': round(p50, 2),
        'p75': round(p75, 2),
        'p90': round(p90, 2),
        'uit_2026': float(UIT_2026),
        # JSON para gráficos
        'dist_labels': json.dumps(dist_labels),
        'dist_values': json.dumps(dist_values),
        'area_labels': json.dumps(area_labels),
        'area_avg_values': json.dumps(area_avg_values),
        'uit_labels': json.dumps(uit_labels),
        'uit_values': json.dumps(uit_values),
        # Tablas
        'top5': top5,
        'bottom5': bottom5,
        'percentiles': [
            ('P25', round(p25, 2)),
            ('P50 (Mediana)', round(p50, 2)),
            ('P75', round(p75, 2)),
            ('P90', round(p90, 2)),
        ],
    }
    return render(request, 'analytics/salary_analytics.html', context)


# ─────────────────────────────────────────────────
# API RESUMEN AJAX (para widgets de home)
# ─────────────────────────────────────────────────

@solo_admin
def analytics_resumen_ajax(request):
    """Retorna resumen rápido de KPIs para widgets embebidos en otras páginas."""
    from personal.models import Personal

    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)

    activos = Personal.objects.filter(estado='Activo')
    headcount_hoy = activos.count()
    nuevos_mes = Personal.objects.filter(
        fecha_alta__gte=inicio_mes, fecha_alta__lte=hoy
    ).count()
    bajas_mes = Personal.objects.filter(
        fecha_cese__gte=inicio_mes, fecha_cese__lte=hoy,
        estado='Cesado'
    ).count()

    ausentismo_pct = None
    try:
        from asistencia.models import RegistroTareo
        registros = RegistroTareo.objects.filter(
            fecha__gte=inicio_mes, fecha__lte=hoy)
        total_reg = registros.count()
        faltas = registros.filter(codigo_dia__in=['F', 'FALTA']).count()
        if total_reg > 0:
            ausentismo_pct = round(faltas / total_reg * 100, 1)
    except Exception:
        pass

    return JsonResponse({
        'headcount_hoy': headcount_hoy,
        'nuevos_mes': nuevos_mes,
        'bajas_mes': bajas_mes,
        'ausentismo_pct': ausentismo_pct,
    })


# ─────────────────────────────────────────────────
# SNAPSHOTS KPI
# ─────────────────────────────────────────────────

@solo_admin
def snapshots_list(request):
    """Lista de snapshots KPI mensuales."""
    snapshots = KPISnapshot.objects.all()[:24]
    return render(request, 'analytics/snapshots.html', {'snapshots': snapshots})


@solo_admin
def generar_snapshot_view(request):
    """Genera snapshot KPI del mes actual (POST)."""
    if request.method == 'POST':
        hoy = date.today()
        snapshot = generar_snapshot(hoy.year, hoy.month, request.user)
        messages.success(request, f"Snapshot KPI generado para {hoy.strftime('%B %Y')}.")
        return redirect('analytics_snapshots')
    return redirect('analytics_dashboard')


# ─────────────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────────────

@solo_admin
def alertas_list(request):
    """Lista de alertas RRHH."""
    estado = request.GET.get('estado', 'ACTIVA')
    alertas = AlertaRRHH.objects.all()
    if estado != 'TODAS':
        alertas = alertas.filter(estado=estado)
    return render(request, 'analytics/alertas.html', {
        'alertas': alertas[:50],
        'estado_filtro': estado,
    })


@solo_admin
def resolver_alerta(request, pk):
    """Marcar alerta como resuelta (POST)."""
    if request.method == 'POST':
        alerta = get_object_or_404(AlertaRRHH, pk=pk)
        alerta.estado = 'RESUELTA'
        alerta.resuelta_por = request.user
        alerta.fecha_resolucion = timezone.now()
        alerta.notas_resolucion = request.POST.get('notas', '')
        alerta.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
        messages.success(request, "Alerta marcada como resuelta.")
    return redirect('analytics_alertas')


@solo_admin
def generar_alertas_view(request):
    """Ejecuta generación de alertas (POST)."""
    if request.method == 'POST':
        alertas = generar_alertas()
        messages.success(request, f"Se generaron {len(alertas)} alerta(s) nuevas.")
    return redirect('analytics_alertas')


# ─────────────────────────────────────────────────
# API ENDPOINTS (para gráficos AJAX)
# ─────────────────────────────────────────────────

@solo_admin
def api_kpi_actual(request):
    """Retorna KPIs en tiempo real como JSON."""
    from personal.models import Personal

    activos = Personal.objects.filter(estado='Activo')
    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)

    data = {
        'total_empleados': activos.count(),
        'staff': activos.filter(grupo_tareo='STAFF').count(),
        'rco': activos.filter(grupo_tareo='RCO').count(),
        'altas_mes': Personal.objects.filter(
            fecha_alta__gte=inicio_mes).count(),
        'bajas_mes': Personal.objects.filter(
            fecha_cese__gte=inicio_mes, estado='Cesado').count(),
    }
    return JsonResponse(data)


@solo_admin
def ai_dashboard(request):
    """Dashboard ejecutivo con gráficos + análisis IA."""
    from personal.models import Personal, Area

    activos = Personal.objects.filter(estado='Activo')
    total = activos.count()
    staff = activos.filter(grupo_tareo='STAFF').count()
    rco = activos.filter(grupo_tareo='RCO').count()

    hoy = date.today()
    inicio_mes = date(hoy.year, hoy.month, 1)

    altas_mes = Personal.objects.filter(
        fecha_alta__gte=inicio_mes, fecha_alta__lte=hoy).count()
    bajas_mes = Personal.objects.filter(
        fecha_cese__gte=inicio_mes, fecha_cese__lte=hoy, estado='Cesado').count()

    # Distribución por área
    areas_data = (
        activos
        .values('subarea__area__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    areas_labels = [a['subarea__area__nombre'] or 'Sin Área' for a in areas_data]
    areas_values = [a['total'] for a in areas_data]

    # Tendencia histórica
    snapshots = KPISnapshot.objects.order_by('-periodo')[:12][::-1]
    trend_labels = [s.periodo.strftime('%b %Y') for s in snapshots]
    trend_headcount = [s.total_empleados for s in snapshots]
    trend_rotacion = [float(s.tasa_rotacion) for s in snapshots]
    trend_asistencia = [float(s.tasa_asistencia) for s in snapshots]
    trend_he = [float(s.total_he_mes) for s in snapshots]

    # Antigüedad
    antiguedad = {
        'Menos de 1 año': activos.filter(fecha_alta__gte=hoy - timedelta(days=365)).count(),
        '1-3 años': activos.filter(
            fecha_alta__lt=hoy - timedelta(days=365),
            fecha_alta__gte=hoy - timedelta(days=365 * 3)).count(),
        '3-5 años': activos.filter(
            fecha_alta__lt=hoy - timedelta(days=365 * 3),
            fecha_alta__gte=hoy - timedelta(days=365 * 5)).count(),
        '+5 años': activos.filter(fecha_alta__lt=hoy - timedelta(days=365 * 5)).count(),
    }

    context = {
        'total_empleados': total,
        'empleados_staff': staff,
        'empleados_rco': rco,
        'altas_mes': altas_mes,
        'bajas_mes': bajas_mes,
        'areas_labels': json.dumps(areas_labels),
        'areas_values': json.dumps(areas_values),
        'trend_labels': json.dumps(trend_labels),
        'trend_headcount': json.dumps(trend_headcount),
        'trend_rotacion': json.dumps(trend_rotacion),
        'trend_asistencia': json.dumps(trend_asistencia),
        'trend_he': json.dumps(trend_he, cls=DecimalEncoder),
        'antiguedad_labels': json.dumps(list(antiguedad.keys())),
        'antiguedad_values': json.dumps(list(antiguedad.values())),
    }
    return render(request, 'analytics/ai_dashboard.html', context)


@solo_admin
def api_tendencias(request):
    """Retorna tendencias de los últimos N meses."""
    meses = int(request.GET.get('meses', 12))
    snapshots = KPISnapshot.objects.order_by('-periodo')[:meses][::-1]
    data = {
        'labels': [s.periodo.strftime('%b %Y') for s in snapshots],
        'headcount': [s.total_empleados for s in snapshots],
        'rotacion': [float(s.tasa_rotacion) for s in snapshots],
        'asistencia': [float(s.tasa_asistencia) for s in snapshots],
        'he': [float(s.total_he_mes) for s in snapshots],
    }
    return JsonResponse(data)
