"""
Seed de plantillas de notificación por defecto.

Uso:
    python manage.py seed_plantillas_notificacion
"""
from django.core.management.base import BaseCommand

from comunicaciones.models import PlantillaNotificacion


PLANTILLAS = [
    {
        'nombre': 'Bienvenida Onboarding',
        'codigo': 'bienvenida_onboarding',
        'asunto_template': 'Bienvenido a {{ empresa }}',
        'cuerpo_template': (
            '<p>Hola <strong>{{ nombre }}</strong>,</p>'
            '<p>Te damos la bienvenida a <strong>{{ empresa }}</strong>. '
            'Tu cargo es <strong>{{ cargo }}</strong> y tu fecha de inicio es el '
            '<strong>{{ fecha }}</strong>.</p>'
            '<p>Tu proceso de onboarding ya ha comenzado. Ingresa al sistema para '
            'revisar tus tareas pendientes.</p>'
            '<p>Saludos,<br>Equipo de Recursos Humanos</p>'
        ),
        'tipo': 'EMAIL',
        'modulo': 'ONBOARDING',
        'variables_disponibles': '{{ nombre }}, {{ cargo }}, {{ empresa }}, {{ fecha }}',
    },
    {
        'nombre': 'Evaluación Asignada',
        'codigo': 'evaluacion_asignada',
        'asunto_template': 'Se te ha asignado una evaluación: {{ ciclo }}',
        'cuerpo_template': (
            '<p>Hola <strong>{{ nombre }}</strong>,</p>'
            '<p>Se te ha asignado una evaluación de desempeño en el ciclo '
            '<strong>{{ ciclo }}</strong>.</p>'
            '<p>Fecha límite: <strong>{{ fecha_limite }}</strong></p>'
            '<p>Ingresa al portal para completarla.</p>'
        ),
        'tipo': 'IN_APP',
        'modulo': 'EVALUACIONES',
        'variables_disponibles': '{{ nombre }}, {{ ciclo }}, {{ fecha_limite }}',
    },
    {
        'nombre': 'Encuesta Pendiente',
        'codigo': 'encuesta_pendiente',
        'asunto_template': 'Tienes una encuesta pendiente: {{ encuesta }}',
        'cuerpo_template': (
            '<p>Hola <strong>{{ nombre }}</strong>,</p>'
            '<p>Tienes una encuesta pendiente: <strong>{{ encuesta }}</strong>.</p>'
            '<p>Fecha límite: <strong>{{ fecha_limite }}</strong></p>'
            '<p>Tu participación es importante. Ingresa al portal para responderla.</p>'
        ),
        'tipo': 'IN_APP',
        'modulo': 'ENCUESTAS',
        'variables_disponibles': '{{ nombre }}, {{ encuesta }}, {{ fecha_limite }}',
    },
    {
        'nombre': 'Vacaciones Aprobadas',
        'codigo': 'vacaciones_aprobadas',
        'asunto_template': 'Tu solicitud de vacaciones fue aprobada',
        'cuerpo_template': (
            '<p>Hola <strong>{{ nombre }}</strong>,</p>'
            '<p>Tu solicitud de vacaciones ha sido <strong>aprobada</strong>.</p>'
            '<p>Período: <strong>{{ fecha_inicio }}</strong> al <strong>{{ fecha_fin }}</strong> '
            '({{ dias }} días)</p>'
            '<p>Aprobado por: {{ aprobador }}</p>'
            '<p>Saludos,<br>Equipo de Recursos Humanos</p>'
        ),
        'tipo': 'EMAIL',
        'modulo': 'VACACIONES',
        'variables_disponibles': '{{ nombre }}, {{ fecha_inicio }}, {{ fecha_fin }}, {{ dias }}, {{ aprobador }}',
    },
    {
        'nombre': 'Vacaciones Rechazadas',
        'codigo': 'vacaciones_rechazadas',
        'asunto_template': 'Tu solicitud de vacaciones fue rechazada',
        'cuerpo_template': (
            '<p>Hola <strong>{{ nombre }}</strong>,</p>'
            '<p>Lamentamos informarte que tu solicitud de vacaciones ha sido '
            '<strong>rechazada</strong>.</p>'
            '<p>Período solicitado: <strong>{{ fecha_inicio }}</strong> al '
            '<strong>{{ fecha_fin }}</strong></p>'
            '<p>Motivo: {{ motivo }}</p>'
            '<p>Si tienes preguntas, comunícate con tu responsable de área.</p>'
        ),
        'tipo': 'EMAIL',
        'modulo': 'VACACIONES',
        'variables_disponibles': '{{ nombre }}, {{ fecha_inicio }}, {{ fecha_fin }}, {{ motivo }}',
    },
    {
        'nombre': 'Medida Disciplinaria',
        'codigo': 'medida_disciplinaria',
        'asunto_template': 'Notificación de medida disciplinaria',
        'cuerpo_template': (
            '<p>Estimado(a) <strong>{{ nombre }}</strong>,</p>'
            '<p>Se le comunica que se ha registrado una medida disciplinaria:</p>'
            '<p><strong>Tipo de falta:</strong> {{ tipo_falta }}<br>'
            '<strong>Fecha:</strong> {{ fecha }}<br>'
            '<strong>Medida:</strong> {{ medida }}</p>'
            '<p>Tiene derecho a presentar sus descargos conforme al procedimiento '
            'establecido (DS 003-97-TR).</p>'
        ),
        'tipo': 'EMAIL',
        'modulo': 'DISCIPLINARIA',
        'variables_disponibles': '{{ nombre }}, {{ tipo_falta }}, {{ fecha }}, {{ medida }}',
    },
    {
        'nombre': 'Préstamo Aprobado',
        'codigo': 'prestamo_aprobado',
        'asunto_template': 'Tu préstamo ha sido aprobado',
        'cuerpo_template': (
            '<p>Hola <strong>{{ nombre }}</strong>,</p>'
            '<p>Tu solicitud de préstamo ha sido <strong>aprobada</strong>.</p>'
            '<p><strong>Monto:</strong> {{ monto }}<br>'
            '<strong>Cuotas:</strong> {{ cuotas }}<br>'
            '<strong>Monto por cuota:</strong> {{ monto_cuota }}</p>'
            '<p>El descuento iniciará en la próxima nómina.</p>'
        ),
        'tipo': 'EMAIL',
        'modulo': 'RRHH',
        'variables_disponibles': '{{ nombre }}, {{ monto }}, {{ cuotas }}, {{ monto_cuota }}',
    },
    {
        'nombre': 'Comunicado General',
        'codigo': 'comunicado_general',
        'asunto_template': 'Nuevo comunicado: {{ titulo }}',
        'cuerpo_template': (
            '<p>Se ha publicado un nuevo comunicado:</p>'
            '<h3>{{ titulo }}</h3>'
            '<div>{{ contenido }}</div>'
            '<p>Ingresa al portal para más detalles.</p>'
        ),
        'tipo': 'AMBOS',
        'modulo': 'SISTEMA',
        'variables_disponibles': '{{ titulo }}, {{ contenido }}',
    },
]


class Command(BaseCommand):
    help = 'Crea las plantillas de notificación por defecto'

    def handle(self, *args, **options):
        creadas = 0
        existentes = 0

        for data in PLANTILLAS:
            _, created = PlantillaNotificacion.objects.get_or_create(
                codigo=data['codigo'],
                defaults=data,
            )
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f"  Creada: {data['nombre']}"))
            else:
                existentes += 1
                self.stdout.write(f"  Ya existe: {data['nombre']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nPlantillas: {creadas} creadas, {existentes} ya existían."
        ))
