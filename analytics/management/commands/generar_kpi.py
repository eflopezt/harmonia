"""
Management command: Genera snapshot KPI del mes actual (o mes especificado).

Uso:
    python manage.py generar_kpi              # mes actual
    python manage.py generar_kpi --mes 2 --anio 2026
"""
from datetime import date
from django.core.management.base import BaseCommand
from analytics.services import generar_snapshot, generar_alertas


class Command(BaseCommand):
    help = 'Genera snapshot KPI mensual y alertas automáticas'

    def add_arguments(self, parser):
        parser.add_argument('--anio', type=int, default=None)
        parser.add_argument('--mes', type=int, default=None)
        parser.add_argument('--alertas', action='store_true', help='También generar alertas')

    def handle(self, *args, **options):
        hoy = date.today()
        anio = options['anio'] or hoy.year
        mes = options['mes'] or hoy.month

        self.stdout.write(f"Generando KPI para {mes:02d}/{anio}...")
        snapshot = generar_snapshot(anio, mes)
        self.stdout.write(self.style.SUCCESS(
            f"✓ Snapshot generado: {snapshot.total_empleados} empleados, "
            f"rotación {snapshot.tasa_rotacion}%, "
            f"asistencia {snapshot.tasa_asistencia}%"
        ))

        if options['alertas']:
            alertas = generar_alertas()
            self.stdout.write(self.style.SUCCESS(
                f"✓ {len(alertas)} alertas generadas"
            ))
