# Data migration: seed WhatsApp notification templates

from django.db import migrations


def crear_plantillas_whatsapp(apps, schema_editor):
    PlantillaNotificacion = apps.get_model('comunicaciones', 'PlantillaNotificacion')

    templates = [
        {
            'nombre': 'Vacaciones Aprobadas (WhatsApp)',
            'codigo': 'whatsapp_vacacion_aprobada',
            'asunto_template': 'Vacaciones aprobadas',
            'cuerpo_template': (
                'Hola {{ nombre }}, tu solicitud de vacaciones ha sido *aprobada*.\n\n'
                'Periodo: {{ fecha_inicio }} al {{ fecha_fin }}\n'
                'Dias: {{ dias }}\n\n'
                'Recuerda coordinar la entrega de pendientes con tu jefe directo.\n'
                '-- Harmoni RRHH'
            ),
            'tipo': 'WHATSAPP',
            'modulo': 'VACACIONES',
            'activa': True,
            'variables_disponibles': '{{ nombre }}, {{ fecha_inicio }}, {{ fecha_fin }}, {{ dias }}',
        },
        {
            'nombre': 'Vacaciones Rechazadas (WhatsApp)',
            'codigo': 'whatsapp_vacacion_rechazada',
            'asunto_template': 'Vacaciones rechazadas',
            'cuerpo_template': (
                'Hola {{ nombre }}, tu solicitud de vacaciones del {{ fecha_inicio }} al {{ fecha_fin }} '
                'ha sido *rechazada*.\n\n'
                '{% if motivo %}Motivo: {{ motivo }}\n\n{% endif %}'
                'Comunicate con tu jefe directo para mas detalles.\n'
                '-- Harmoni RRHH'
            ),
            'tipo': 'WHATSAPP',
            'modulo': 'VACACIONES',
            'activa': True,
            'variables_disponibles': '{{ nombre }}, {{ fecha_inicio }}, {{ fecha_fin }}, {{ motivo }}',
        },
        {
            'nombre': 'Boleta de Pago Disponible (WhatsApp)',
            'codigo': 'whatsapp_boleta_disponible',
            'asunto_template': 'Boleta de pago disponible',
            'cuerpo_template': (
                'Hola {{ nombre }}, tu boleta de pago de *{{ periodo }}* ya esta disponible.\n\n'
                'Monto neto: {{ monto_neto }}\n\n'
                'Descargala desde el portal de empleados.\n'
                '-- Harmoni RRHH'
            ),
            'tipo': 'WHATSAPP',
            'modulo': 'RRHH',
            'activa': True,
            'variables_disponibles': '{{ nombre }}, {{ periodo }}, {{ monto_neto }}',
        },
        {
            'nombre': 'Feliz Cumpleanos (WhatsApp)',
            'codigo': 'whatsapp_cumpleanos',
            'asunto_template': 'Feliz cumpleanos',
            'cuerpo_template': (
                'Feliz cumpleanos {{ nombre }}!\n\n'
                'Todo el equipo te desea un excelente dia. '
                'Que este nuevo ano de vida te traiga muchos exitos.\n\n'
                '-- Tu equipo de {{ empresa }}'
            ),
            'tipo': 'WHATSAPP',
            'modulo': 'RRHH',
            'activa': True,
            'variables_disponibles': '{{ nombre }}, {{ empresa }}',
        },
        {
            'nombre': 'Contrato por Vencer (WhatsApp)',
            'codigo': 'whatsapp_contrato_por_vencer',
            'asunto_template': 'Contrato por vencer',
            'cuerpo_template': (
                'Hola {{ nombre }}, tu contrato vence el *{{ fecha_vencimiento }}* '
                '({{ dias_restantes }} dias restantes).\n\n'
                'El area de RRHH se comunicara contigo para coordinar la renovacion.\n'
                '-- Harmoni RRHH'
            ),
            'tipo': 'WHATSAPP',
            'modulo': 'RRHH',
            'activa': True,
            'variables_disponibles': '{{ nombre }}, {{ fecha_vencimiento }}, {{ dias_restantes }}',
        },
    ]

    for t in templates:
        PlantillaNotificacion.objects.get_or_create(
            codigo=t['codigo'],
            defaults=t,
        )


def eliminar_plantillas_whatsapp(apps, schema_editor):
    PlantillaNotificacion = apps.get_model('comunicaciones', 'PlantillaNotificacion')
    PlantillaNotificacion.objects.filter(codigo__startswith='whatsapp_').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('comunicaciones', '0003_whatsapp_fields'),
    ]

    operations = [
        migrations.RunPython(crear_plantillas_whatsapp, eliminar_plantillas_whatsapp),
    ]
