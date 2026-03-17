"""
Analytics — Servicios de cálculo de KPIs.

Genera snapshots mensuales a partir de datos reales de los módulos.
Cada función calcula métricas específicas sin dependencia entre ellas.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone

logger = logging.getLogger('analytics.services')


def calcular_headcount(periodo_inicio, periodo_fin):
    """Retorna métricas de headcount para un periodo."""
    from personal.models import Personal

    activos = Personal.objects.filter(estado='Activo')
    total = activos.count()
    staff = activos.filter(grupo_tareo='STAFF').count()
    rco = activos.filter(grupo_tareo='RCO').count()

    altas = Personal.objects.filter(
        fecha_alta__gte=periodo_inicio,
        fecha_alta__lte=periodo_fin
    ).count()

    bajas = Personal.objects.filter(
        fecha_cese__gte=periodo_inicio,
        fecha_cese__lte=periodo_fin,
        estado='Cesado'
    ).count()

    return {
        'total_empleados': total,
        'empleados_staff': staff,
        'empleados_rco': rco,
        'altas_mes': altas,
        'bajas_mes': bajas,
    }


def calcular_rotacion(periodo_inicio, periodo_fin):
    """Tasa de rotación mensual y voluntaria."""
    from personal.models import Personal

    total_promedio = Personal.objects.filter(
        Q(estado='Activo') |
        Q(fecha_cese__gte=periodo_inicio, fecha_cese__lte=periodo_fin)
    ).count()

    if total_promedio == 0:
        return {'tasa_rotacion': Decimal('0'), 'tasa_rotacion_voluntaria': Decimal('0')}

    bajas_total = Personal.objects.filter(
        fecha_cese__gte=periodo_inicio,
        fecha_cese__lte=periodo_fin,
        estado='Cesado',
    ).count()

    # No hay campo motivo_cese — tasa voluntaria se estima igual a total
    # hasta integrar con futuro módulo de offboarding
    bajas_voluntarias = bajas_total

    tasa = Decimal(str(round(bajas_total / total_promedio * 100, 2)))
    tasa_vol = Decimal(str(round(bajas_voluntarias / total_promedio * 100, 2)))

    return {'tasa_rotacion': tasa, 'tasa_rotacion_voluntaria': tasa_vol}


def calcular_asistencia(periodo_inicio, periodo_fin):
    """Métricas de asistencia y horas extra."""
    from asistencia.models import RegistroTareo

    registros = RegistroTareo.objects.filter(
        fecha__gte=periodo_inicio,
        fecha__lte=periodo_fin,
    )

    total_registros = registros.count()
    asistidos = registros.exclude(
        codigo_dia__in=['F', 'FALTA', 'SIN_MARCACION', 'FERIADO']
    ).count()

    tasa = Decimal('0')
    if total_registros > 0:
        tasa = Decimal(str(round(asistidos / total_registros * 100, 2)))

    he_agg = registros.aggregate(
        total_he=Sum(
            F('he_25') + F('he_35') + F('he_100'),
            default=Decimal('0')
        ),
    )
    total_he = he_agg['total_he'] or Decimal('0')

    # Promedio HE por persona
    personas_con_he = registros.filter(
        Q(he_25__gt=0) | Q(he_35__gt=0) | Q(he_100__gt=0)
    ).values('personal').distinct().count()

    promedio = Decimal('0')
    if personas_con_he > 0:
        promedio = Decimal(str(round(float(total_he) / personas_con_he, 2)))

    return {
        'tasa_asistencia': tasa,
        'total_he_mes': total_he,
        'promedio_he_persona': promedio,
    }


def calcular_vacaciones():
    """Métricas de vacaciones pendientes."""
    try:
        from vacaciones.models import SaldoVacacional
        saldos = SaldoVacacional.objects.filter(estado='VIGENTE')
        agg = saldos.aggregate(
            total_pendientes=Sum('dias_pendientes', default=0),
            promedio=Avg('dias_pendientes', default=0),
        )
        return {
            'dias_vacaciones_pendientes': agg['total_pendientes'] or 0,
            'promedio_dias_pendientes': Decimal(str(round(float(agg['promedio'] or 0), 1))),
        }
    except Exception:
        return {'dias_vacaciones_pendientes': 0, 'promedio_dias_pendientes': Decimal('0')}


def calcular_capacitacion(periodo_inicio, periodo_fin):
    """Métricas de capacitación del periodo."""
    try:
        from capacitaciones.models import Capacitacion, AsistenciaCapacitacion
        from personal.models import Personal

        caps = Capacitacion.objects.filter(
            fecha_inicio__gte=periodo_inicio,
            fecha_fin__lte=periodo_fin,
            estado='COMPLETADA',
        )
        horas = caps.aggregate(total=Sum('horas', default=Decimal('0')))['total'] or Decimal('0')

        asistentes = AsistenciaCapacitacion.objects.filter(
            capacitacion__in=caps,
            asistio=True,
        ).values('personal').distinct().count()

        total_activos = Personal.objects.filter(estado='Activo').count()
        cobertura = Decimal('0')
        if total_activos > 0:
            cobertura = Decimal(str(round(asistentes / total_activos * 100, 2)))

        return {
            'horas_capacitacion_mes': horas,
            'empleados_capacitados': asistentes,
            'cobertura_capacitacion': cobertura,
        }
    except Exception:
        return {
            'horas_capacitacion_mes': Decimal('0'),
            'empleados_capacitados': 0,
            'cobertura_capacitacion': Decimal('0'),
        }


def generar_snapshot(anio, mes, usuario=None):
    """
    Genera (o actualiza) el snapshot KPI de un mes/año.
    Retorna la instancia KPISnapshot creada/actualizada.
    """
    from .models import KPISnapshot

    periodo = date(anio, mes, 1)
    if mes == 12:
        periodo_fin = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        periodo_fin = date(anio, mes + 1, 1) - timedelta(days=1)

    data = {}
    data.update(calcular_headcount(periodo, periodo_fin))
    data.update(calcular_rotacion(periodo, periodo_fin))
    data.update(calcular_asistencia(periodo, periodo_fin))
    data.update(calcular_vacaciones())
    data.update(calcular_capacitacion(periodo, periodo_fin))

    data['generado_por'] = usuario

    snapshot, created = KPISnapshot.objects.update_or_create(
        periodo=periodo,
        defaults=data,
    )
    return snapshot


def generar_alertas():
    """
    Revisa condiciones y genera alertas automáticas.
    Ejecutar periódicamente (diario o semanal).
    """
    from .models import AlertaRRHH
    from personal.models import Personal, Area

    alertas_creadas = []

    # ── Alerta: Vacaciones acumuladas > 30 días ──
    try:
        from vacaciones.models import SaldoVacacional
        criticos = SaldoVacacional.objects.filter(
            estado='VIGENTE', dias_pendientes__gte=30
        ).select_related('personal__subarea__area')

        for saldo in criticos[:20]:  # limitar
            area = getattr(saldo.personal.subarea, 'area', None) if hasattr(saldo.personal, 'subarea') and saldo.personal.subarea else None
            alerta, created = AlertaRRHH.objects.get_or_create(
                titulo=f"Vacaciones acumuladas: {saldo.personal.apellidos_nombres}",
                categoria='VACACIONES',
                estado='ACTIVA',
                defaults={
                    'descripcion': f"{saldo.personal.apellidos_nombres} tiene {saldo.dias_pendientes} días de vacaciones pendientes.",
                    'severidad': 'WARN' if saldo.dias_pendientes < 45 else 'CRITICAL',
                    'area': area,
                    'valor_actual': Decimal(str(saldo.dias_pendientes)),
                    'valor_umbral': Decimal('30'),
                },
            )
            if created:
                alertas_creadas.append(alerta)
    except Exception as exc:
        logger.warning('Error generando alertas de vacaciones: %s', exc)

    # ── Alerta: Documentos vencidos ──
    try:
        from documentos.models import DocumentoTrabajador
        hoy = date.today()
        vencidos = DocumentoTrabajador.objects.filter(
            fecha_vencimiento__lt=hoy,
            estado='VIGENTE',
        ).count()
        if vencidos > 0:
            alerta, created = AlertaRRHH.objects.get_or_create(
                titulo=f"{vencidos} documentos vencidos",
                categoria='DOCUMENTOS',
                estado='ACTIVA',
                defaults={
                    'descripcion': f"Existen {vencidos} documentos con fecha de vencimiento pasada que requieren renovación.",
                    'severidad': 'WARN' if vencidos < 10 else 'CRITICAL',
                    'valor_actual': Decimal(str(vencidos)),
                },
            )
            if created:
                alertas_creadas.append(alerta)
    except Exception as exc:
        logger.warning('Error generando alertas de documentos: %s', exc)

    # ── Alerta: Contratos por vencer ──────────────────────────────────
    try:
        from dateutil.relativedelta import relativedelta
        hoy = date.today()
        umbrales = [7, 15, 30]
        for dias in umbrales:
            limite = hoy + timedelta(days=dias)
            por_vencer = Personal.objects.filter(
                estado='Activo',
                fecha_fin_contrato__gte=hoy,
                fecha_fin_contrato__lte=limite,
            ).count()
            if por_vencer > 0:
                titulo = f"{por_vencer} contrato(s) vence(n) en {dias} días"
                alerta, created = AlertaRRHH.objects.get_or_create(
                    titulo=titulo,
                    categoria='CONTRATOS',
                    estado='ACTIVA',
                    defaults={
                        'descripcion': (
                            f"Hay {por_vencer} contrato(s) laboral(es) que vencen "
                            f"antes del {limite.strftime('%d/%m/%Y')}. "
                            f"Revisar renovación o desvinculación."
                        ),
                        'severidad': 'CRITICAL' if dias <= 7 else ('WARN' if dias <= 15 else 'INFO'),
                        'valor_actual': Decimal(str(por_vencer)),
                        'valor_umbral': Decimal(str(dias)),
                    },
                )
                if created:
                    alertas_creadas.append(alerta)
                break  # solo la alerta más urgente (menor umbral que aplica)
    except Exception as exc:
        logger.warning('Error generando alertas de contratos por vencer: %s', exc)

    # ── Alerta: Contratos vencidos sin renovar ────────────────────────
    try:
        hoy = date.today()
        vencidos_contrato = Personal.objects.filter(
            estado='Activo',
            fecha_fin_contrato__lt=hoy,
        ).count()
        if vencidos_contrato > 0:
            alerta, created = AlertaRRHH.objects.get_or_create(
                titulo=f"{vencidos_contrato} contrato(s) VENCIDO(s) sin renovar",
                categoria='CONTRATOS',
                estado='ACTIVA',
                defaults={
                    'descripcion': (
                        f"{vencidos_contrato} trabajador(es) activo(s) tiene(n) "
                        f"contrato vencido. Regularizar urgente."
                    ),
                    'severidad': 'CRITICAL',
                    'valor_actual': Decimal(str(vencidos_contrato)),
                },
            )
            if created:
                alertas_creadas.append(alerta)
    except Exception as exc:
        logger.warning('Error generando alertas de contratos vencidos: %s', exc)

    # ── Alerta: Período de prueba por terminar (<= 15 días) ───────────
    try:
        from dateutil.relativedelta import relativedelta
        hoy = date.today()
        # Buscamos empleados activos ingresados hace 2.5 a 11.5 meses (approx)
        # Período de prueba de al menos 3 meses
        desde = hoy - relativedelta(months=12)
        candidatos = Personal.objects.filter(estado='Activo', fecha_alta__gte=desde)

        proximos_prueba = 0
        for p in candidatos:
            fin = p.fecha_fin_periodo_prueba
            if fin:
                dias = (fin - hoy).days
                if 0 <= dias <= 15:
                    proximos_prueba += 1

        if proximos_prueba > 0:
            alerta, created = AlertaRRHH.objects.get_or_create(
                titulo=f"{proximos_prueba} período(s) de prueba finalizan en 15 días",
                categoria='CONTRATOS',
                estado='ACTIVA',
                defaults={
                    'descripcion': (
                        f"{proximos_prueba} trabajador(es) están a punto de superar "
                        f"su período de prueba. Evaluar continuidad."
                    ),
                    'severidad': 'INFO',
                    'valor_actual': Decimal(str(proximos_prueba)),
                    'valor_umbral': Decimal('15'),
                },
            )
            if created:
                alertas_creadas.append(alerta)
    except Exception as exc:
        logger.warning('Error generando alertas de período de prueba: %s', exc)

    return alertas_creadas
