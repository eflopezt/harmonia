"""Carga competencias base estándar."""
from django.core.management.base import BaseCommand
from evaluaciones.models import Competencia


COMPETENCIAS = [
    # Core / Organizacionales
    {'nombre': 'Compromiso Organizacional', 'codigo': 'compromiso', 'categoria': 'CORE', 'descripcion': 'Grado de identificación y dedicación a la empresa'},
    {'nombre': 'Orientación a Resultados', 'codigo': 'resultados', 'categoria': 'CORE', 'descripcion': 'Capacidad de alcanzar metas y objetivos planteados'},
    {'nombre': 'Trabajo en Equipo', 'codigo': 'equipo', 'categoria': 'INTERPERSONAL', 'descripcion': 'Habilidad para colaborar y aportar al logro grupal'},
    {'nombre': 'Comunicación Efectiva', 'codigo': 'comunicacion', 'categoria': 'INTERPERSONAL', 'descripcion': 'Claridad y asertividad en la transmisión de ideas'},
    {'nombre': 'Integridad y Ética', 'codigo': 'integridad', 'categoria': 'CORE', 'descripcion': 'Actuar con honestidad, transparencia y responsabilidad'},
    {'nombre': 'Adaptabilidad al Cambio', 'codigo': 'adaptabilidad', 'categoria': 'CORE', 'descripcion': 'Flexibilidad ante nuevas situaciones y retos'},
    # Liderazgo
    {'nombre': 'Liderazgo', 'codigo': 'liderazgo', 'categoria': 'LIDERAZGO', 'descripcion': 'Capacidad de influir positivamente y guiar al equipo'},
    {'nombre': 'Toma de Decisiones', 'codigo': 'decisiones', 'categoria': 'LIDERAZGO', 'descripcion': 'Análisis y resolución oportuna de situaciones'},
    {'nombre': 'Desarrollo de Personas', 'codigo': 'desarrollo', 'categoria': 'LIDERAZGO', 'descripcion': 'Fomento del crecimiento profesional del equipo'},
    {'nombre': 'Gestión del Conflicto', 'codigo': 'conflicto', 'categoria': 'LIDERAZGO', 'descripcion': 'Manejo constructivo de diferencias y desacuerdos'},
    # Técnicas
    {'nombre': 'Conocimiento Técnico', 'codigo': 'tecnico', 'categoria': 'TECNICA', 'descripcion': 'Dominio de conocimientos propios del cargo'},
    {'nombre': 'Orientación a la Calidad', 'codigo': 'calidad', 'categoria': 'TECNICA', 'descripcion': 'Cumplimiento de estándares y mejora continua'},
    {'nombre': 'Innovación', 'codigo': 'innovacion', 'categoria': 'TECNICA', 'descripcion': 'Propuesta de ideas y soluciones creativas'},
    {'nombre': 'Planificación y Organización', 'codigo': 'planificacion', 'categoria': 'TECNICA', 'descripcion': 'Gestión eficiente del tiempo y recursos'},
    # Interpersonales
    {'nombre': 'Servicio al Cliente Interno', 'codigo': 'servicio', 'categoria': 'INTERPERSONAL', 'descripcion': 'Atención y soporte a colegas y áreas internas'},
    {'nombre': 'Relaciones Interpersonales', 'codigo': 'relaciones', 'categoria': 'INTERPERSONAL', 'descripcion': 'Habilidad para construir y mantener relaciones positivas'},
]


class Command(BaseCommand):
    help = 'Carga competencias base para evaluaciones de desempeño'

    def handle(self, *args, **options):
        creados = 0
        for i, data in enumerate(COMPETENCIAS, 1):
            _, created = Competencia.objects.get_or_create(
                codigo=data['codigo'],
                defaults={**data, 'orden': i * 10},
            )
            if created:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f'{creados} competencias creadas.'))
