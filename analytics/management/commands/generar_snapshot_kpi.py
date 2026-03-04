"""
Management command: Genera snapshot KPI del mes actual (o mes especificado).

Calcula:
  - headcount, staff_count, rco_count
  - tasa_asistencia_promedio (de RegistroTareo del mes)
  - rotacion_mensual (bajas del mes / headcount * 100)

Uso:
    python manage.py generar_snapshot_kpi
    python manage.py generar_snapshot_kpi --mes 2 --anio 2026
    python manage.py generar_snapshot_kpi --alertas
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Genera snapshot KPI mensual con headcount, asistencia y rotación'

    def add_arguments(self, parser):
        parser.add_argument('--anio', type=int, default=None,
                            help='Año del periodo (default: año actual)')
        parser.add_argument('--mes', type=int, default=None,
                            help='Mes del periodo 1-12 (default: mes actual)')
        parser.add_argument('--alertas', action='store_true',
                            help='También ejecutar generación de alertas automáticas')

    def handle(self, *args, **options):
        hoy = date.today()
        anio = options['anio'] or hoy.year
        mes  = options['mes']  or hoy.month

        periodo_inicio = date(anio, mes, 1)
        if mes == 12:
            periodo_fin = date(anio + 1, 1, 1) - timedelta(days=1)
        else:
            periodo_fin = date(anio, mes + 1, 1) - timedelta(days=1)

        self.stdout.write(f"Calculando KPI para {mes:02d}/{anio} "
                          f"({periodo_inicio} al {periodo_fin})...")

        # ── Headcount ──────────────────────────────────────────────────
        from personal.models import Personal

        activos = Personal.objects.filter(estado='Activo')
        headcount  = activos.count()
        staff_count = activos.filter(grupo_tareo='STAFF').count()
        rco_count   = activos.filter(grupo_tareo='RCO').count()

        altas = Personal.objects.filter(
            fecha_alta__gte=periodo_inicio,
            fecha_alta__lte=periodo_fin,
        ).count()

        bajas = Personal.objects.filter(
            fecha_cese__gte=periodo_inicio,
            fecha_cese__lte=periodo_fin,
            estado='Cesado',
        ).count()

        self.stdout.write(f"  Headcount : {headcount} (STAFF {staff_count} / RCO {rco_count})")
        self.stdout.write(f"  Altas mes : {altas}  |  Bajas mes: {bajas}")

        # ── Tasa asistencia (RegistroTareo del mes) ────────────────────
        tasa_asistencia = Decimal('0')
        try:
            from asistencia.models import RegistroTareo

            registros = RegistroTareo.objects.filter(
                fecha__gte=periodo_inicio,
                fecha__lte=periodo_fin,
            )
            total_reg = registros.count()
            asistidos = registros.exclude(
                codigo_dia__in=['F', 'FALTA', 'SIN_MARCACION', 'FERIADO']
            ).count()

            if total_reg > 0:
                tasa_asistencia = Decimal(str(round(asistidos / total_reg * 100, 2)))
            self.stdout.write(f"  Asistencia: {tasa_asistencia}% "
                              f"({asistidos}/{total_reg} registros)")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f"  Asistencia: no calculada ({exc})"))

        # ── Rotación mensual ───────────────────────────────────────────
        tasa_rotacion = Decimal('0')
        try:
            denominador = max(headcount, 1)
            tasa_rotacion = Decimal(str(round(bajas / denominador * 100, 2)))
            self.stdout.write(f"  Rotacion  : {tasa_rotacion}% ({bajas}/{denominador})")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f"  Rotacion: no calculada ({exc})"))

        # ── Guardar snapshot (update_or_create) ────────────────────────
        from analytics.models import KPISnapshot

        snapshot, created = KPISnapshot.objects.update_or_create(
            periodo=periodo_inicio,
            defaults={
                'total_empleados':    headcount,
                'empleados_staff':    staff_count,
                'empleados_rco':      rco_count,
                'altas_mes':          altas,
                'bajas_mes':          bajas,
                'tasa_asistencia':    tasa_asistencia,
                'tasa_rotacion':      tasa_rotacion,
                'tasa_rotacion_voluntaria': tasa_rotacion,
            },
        )

        verb = 'creado' if created else 'actualizado'
        self.stdout.write(self.style.SUCCESS(
            f"\nSnapshot {verb}: {snapshot} "
            f"| headcount={headcount} staff={staff_count} rco={rco_count} "
            f"| asistencia={tasa_asistencia}% rotacion={tasa_rotacion}%"
        ))

        # ── Alertas opcionales ─────────────────────────────────────────
        if options['alertas']:
            self.stdout.write("\nGenerando alertas automáticas...")
            from analytics.services import generar_alertas
            alertas = generar_alertas()
            self.stdout.write(self.style.SUCCESS(
                f"{len(alertas)} alerta(s) nueva(s) generada(s)."))
