"""Carga tipos de falta estándar según legislación peruana."""
from django.core.management.base import BaseCommand
from disciplinaria.models import TipoFalta


TIPOS = [
    # Faltas leves
    {'nombre': 'Tardanza reiterada', 'codigo': 'tardanza', 'gravedad': 'LEVE', 'base_legal': 'Reglamento Interno'},
    {'nombre': 'Incumplimiento de normas de vestimenta', 'codigo': 'vestimenta', 'gravedad': 'LEVE', 'base_legal': 'Reglamento Interno'},
    {'nombre': 'Uso indebido de equipos/recursos', 'codigo': 'uso-indebido-equipos', 'gravedad': 'LEVE', 'base_legal': 'Reglamento Interno'},
    {'nombre': 'Falta de respeto menor', 'codigo': 'falta-respeto-menor', 'gravedad': 'LEVE', 'base_legal': 'Reglamento Interno'},
    # Faltas graves (Art. 25 DS 003-97-TR)
    {'nombre': 'Incumplimiento de obligaciones de trabajo', 'codigo': 'incumplimiento-obligaciones', 'gravedad': 'GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. a)'},
    {'nombre': 'Disminución deliberada del rendimiento', 'codigo': 'disminucion-rendimiento', 'gravedad': 'GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. b)'},
    {'nombre': 'Apropiación de bienes del empleador', 'codigo': 'apropiacion-bienes', 'gravedad': 'MUY_GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. c)'},
    {'nombre': 'Uso/entrega indebida de información', 'codigo': 'info-indebida', 'gravedad': 'GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. d)'},
    {'nombre': 'Concurrencia en estado de embriaguez', 'codigo': 'embriaguez', 'gravedad': 'GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. e)'},
    {'nombre': 'Actos de violencia o faltamiento de palabra', 'codigo': 'violencia', 'gravedad': 'MUY_GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. f)'},
    {'nombre': 'Daño intencional a bienes de la empresa', 'codigo': 'dano-bienes', 'gravedad': 'MUY_GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. g)'},
    {'nombre': 'Abandono de trabajo (más de 3 días consecutivos)', 'codigo': 'abandono', 'gravedad': 'MUY_GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. h)'},
    {'nombre': 'Inasistencia injustificada (más de 5 días en 30)', 'codigo': 'inasistencia-injustificada', 'gravedad': 'GRAVE', 'base_legal': 'DS 003-97-TR Art. 25 inc. h)'},
    {'nombre': 'Hostigamiento sexual', 'codigo': 'hostigamiento-sexual', 'gravedad': 'MUY_GRAVE', 'base_legal': 'Ley 27942 + DS 003-97-TR Art. 25'},
    {'nombre': 'Incumplimiento de normas SSOMA', 'codigo': 'incumplimiento-ssoma', 'gravedad': 'GRAVE', 'base_legal': 'Ley 29783 + DS 005-2012-TR'},
]


class Command(BaseCommand):
    help = 'Carga tipos de falta estándar (DS 003-97-TR + normativa peruana)'

    def handle(self, *args, **options):
        creados = 0
        for data in TIPOS:
            _, created = TipoFalta.objects.get_or_create(
                codigo=data['codigo'],
                defaults=data,
            )
            if created:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f'{creados} tipos de falta creados.'))
