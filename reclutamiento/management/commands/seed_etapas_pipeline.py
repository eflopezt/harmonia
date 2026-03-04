"""
Management command para crear las etapas por defecto del pipeline de seleccion.
"""
from django.core.management.base import BaseCommand
from reclutamiento.models import EtapaPipeline


ETAPAS_DEFAULT = [
    {'nombre': 'Recibido',            'codigo': 'recibido',            'orden': 10, 'color': '#94a3b8', 'eliminable': False},
    {'nombre': 'Filtrado',            'codigo': 'filtrado',            'orden': 20, 'color': '#60a5fa', 'eliminable': True},
    {'nombre': 'Entrevista RRHH',     'codigo': 'entrevista-rrhh',     'orden': 30, 'color': '#a78bfa', 'eliminable': True},
    {'nombre': 'Entrevista Tecnica',  'codigo': 'entrevista-tecnica',  'orden': 40, 'color': '#f472b6', 'eliminable': True},
    {'nombre': 'Evaluacion',          'codigo': 'evaluacion',          'orden': 50, 'color': '#fbbf24', 'eliminable': True},
    {'nombre': 'Oferta',              'codigo': 'oferta',              'orden': 60, 'color': '#34d399', 'eliminable': True},
    {'nombre': 'Contratado',          'codigo': 'contratado',          'orden': 70, 'color': '#22c55e', 'eliminable': False},
    {'nombre': 'Descartado',          'codigo': 'descartado',          'orden': 80, 'color': '#ef4444', 'eliminable': False},
]


class Command(BaseCommand):
    help = 'Crea las etapas por defecto del pipeline de reclutamiento'

    def handle(self, *args, **options):
        creadas = 0
        existentes = 0

        for etapa_data in ETAPAS_DEFAULT:
            obj, created = EtapaPipeline.objects.get_or_create(
                codigo=etapa_data['codigo'],
                defaults=etapa_data,
            )
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f'  + {obj.nombre} (orden {obj.orden})'))
            else:
                existentes += 1
                self.stdout.write(f'  = {obj.nombre} (ya existe)')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Listo: {creadas} creadas, {existentes} ya existian.'
        ))
