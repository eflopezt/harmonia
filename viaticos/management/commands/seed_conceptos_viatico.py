"""
Seed: crea los conceptos de viático estándar.
Referencia: SUNAT, legislación laboral peruana Art. 37° LIR.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from viaticos.models import ConceptoViatico


CONCEPTOS = [
    {
        'nombre': 'Alimentación',
        'codigo': 'alimentacion',
        'descripcion': 'Gastos de alimentación del trabajador en campo.',
        'tope_diario': None,
        'requiere_comprobante': True,
        'afecto_renta': False,
        'orden': 1,
    },
    {
        'nombre': 'Hospedaje',
        'codigo': 'hospedaje',
        'descripcion': 'Alojamiento del trabajador fuera de su residencia habitual.',
        'tope_diario': None,
        'requiere_comprobante': True,
        'afecto_renta': False,
        'orden': 2,
    },
    {
        'nombre': 'Movilidad Local',
        'codigo': 'movilidad-local',
        'descripcion': 'Transporte local en la zona de trabajo (taxi, colectivo).',
        'tope_diario': Decimal('40.00'),
        'requiere_comprobante': False,
        'afecto_renta': False,
        'orden': 3,
    },
    {
        'nombre': 'Combustible',
        'codigo': 'combustible',
        'descripcion': 'Combustible para vehículo asignado.',
        'tope_diario': None,
        'requiere_comprobante': True,
        'afecto_renta': False,
        'orden': 4,
    },
    {
        'nombre': 'Lavandería',
        'codigo': 'lavanderia',
        'descripcion': 'Servicio de lavandería de ropa de trabajo.',
        'tope_diario': Decimal('30.00'),
        'requiere_comprobante': True,
        'afecto_renta': False,
        'orden': 5,
    },
    {
        'nombre': 'Comunicaciones',
        'codigo': 'comunicaciones',
        'descripcion': 'Recargas telefónicas, internet para trabajo.',
        'tope_diario': Decimal('20.00'),
        'requiere_comprobante': False,
        'afecto_renta': False,
        'orden': 6,
    },
    {
        'nombre': 'Otros Gastos',
        'codigo': 'otros-gastos',
        'descripcion': 'Otros gastos no clasificados (peajes, estacionamiento, etc.).',
        'tope_diario': None,
        'requiere_comprobante': True,
        'afecto_renta': False,
        'orden': 10,
    },
]


class Command(BaseCommand):
    help = 'Crea los conceptos de viático iniciales'

    def handle(self, *args, **options):
        creados = 0
        existentes = 0

        for data in CONCEPTOS:
            obj, created = ConceptoViatico.objects.get_or_create(
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
            f'\nConceptos de viático: {creados} creados, {existentes} ya existían.'
        ))
