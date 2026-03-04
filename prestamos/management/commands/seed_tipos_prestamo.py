"""
Seed: crea los tipos de préstamo estándar para la empresa.
Referencia: BUK, Odoo hr_loan, legislación laboral peruana.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from prestamos.models import TipoPrestamo


TIPOS = [
    {
        'nombre': 'Préstamo Personal',
        'codigo': 'prestamo-personal',
        'descripcion': 'Préstamo al trabajador, descontable en cuotas mensuales por nómina.',
        'max_cuotas': 12,
        'tasa_interes_mensual': Decimal('0.000'),
        'monto_maximo': Decimal('10000.00'),
        'requiere_aprobacion': True,
    },
    {
        'nombre': 'Adelanto de Sueldo',
        'codigo': 'adelanto-sueldo',
        'descripcion': 'Adelanto parcial del sueldo mensual. Se descuenta en la próxima nómina.',
        'max_cuotas': 1,
        'tasa_interes_mensual': Decimal('0.000'),
        'monto_maximo': None,
        'requiere_aprobacion': True,
    },
    {
        'nombre': 'Adelanto de Gratificación',
        'codigo': 'adelanto-gratificacion',
        'descripcion': 'Adelanto de gratificación de julio o diciembre (D.Leg. 713). Descuento al pago de gratificación.',
        'max_cuotas': 1,
        'tasa_interes_mensual': Decimal('0.000'),
        'monto_maximo': None,
        'requiere_aprobacion': True,
    },
    {
        'nombre': 'Adelanto de Vacaciones',
        'codigo': 'adelanto-vacaciones',
        'descripcion': 'Adelanto por goce vacacional. Se descuenta al liquidar el período vacacional.',
        'max_cuotas': 1,
        'tasa_interes_mensual': Decimal('0.000'),
        'monto_maximo': None,
        'requiere_aprobacion': True,
    },
    {
        'nombre': 'Préstamo de Emergencia',
        'codigo': 'prestamo-emergencia',
        'descripcion': 'Préstamo por situación de emergencia del trabajador. Trámite expedito con máximo de cuotas reducido.',
        'max_cuotas': 6,
        'tasa_interes_mensual': Decimal('0.000'),
        'monto_maximo': Decimal('5000.00'),
        'requiere_aprobacion': True,
    },
    {
        'nombre': 'Adelanto de CTS',
        'codigo': 'adelanto-cts',
        'descripcion': 'Adelanto a cuenta de la CTS (límite legal: 50% del depósito). Art. 40 D.S. 001-97-TR.',
        'max_cuotas': 1,
        'tasa_interes_mensual': Decimal('0.000'),
        'monto_maximo': None,
        'requiere_aprobacion': True,
    },
]


class Command(BaseCommand):
    help = 'Crea los tipos de préstamo iniciales'

    def handle(self, *args, **options):
        creados = 0
        existentes = 0

        for data in TIPOS:
            obj, created = TipoPrestamo.objects.get_or_create(
                codigo=data['codigo'],
                defaults=data,
            )
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  + {obj.nombre}'))
            else:
                existentes += 1
                self.stdout.write(f'  = {obj.nombre} (ya existe)')

        self.stdout.write(self.style.SUCCESS(
            f'\nTipos de préstamo: {creados} creados, {existentes} ya existían.'
        ))
