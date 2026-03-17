"""
Vistas para WhatsApp — test endpoint y configuracion.
"""
import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from comunicaciones.whatsapp_service import WhatsAppService, WhatsAppTemplates

solo_admin = user_passes_test(lambda u: u.is_superuser, login_url='login')


@login_required
@solo_admin
def whatsapp_config(request):
    """Panel de configuracion WhatsApp con test integrado."""
    from asistencia.models import ConfiguracionSistema

    config = ConfiguracionSistema.objects.filter(pk=1).first()
    provider = getattr(config, 'whatsapp_provider', 'NONE') if config else 'NONE'

    return render(request, 'comunicaciones/whatsapp_config.html', {
        'titulo': 'WhatsApp',
        'config': config,
        'provider': provider,
    })


@login_required
@solo_admin
@require_POST
def whatsapp_test(request):
    """
    Test endpoint: send a test WhatsApp message.

    POST JSON body:
        phone: str (required) — destination phone number
        message: str (optional) — custom message (defaults to test message)
        template: str (optional) — template name from WhatsAppTemplates

    Returns JSON: {ok, provider, detail, message_id}
    """
    try:
        if request.content_type and 'json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST

        phone = data.get('phone', '').strip()
        message = data.get('message', '').strip()
        template = data.get('template', '').strip()

        if not phone:
            return JsonResponse({
                'ok': False,
                'detail': 'Se requiere un numero de telefono (campo "phone")',
            }, status=400)

        # Build message
        if template:
            nombre = data.get('nombre', 'Empleado de Prueba')
            if template == 'vacacion_aprobada':
                message = WhatsAppTemplates.vacacion_aprobada(
                    nombre, '20/03/2026', '27/03/2026', 5
                )
            elif template == 'vacacion_rechazada':
                message = WhatsAppTemplates.vacacion_rechazada(
                    nombre, '20/03/2026', '27/03/2026', 'Periodo de alta demanda'
                )
            elif template == 'boleta_disponible':
                message = WhatsAppTemplates.boleta_disponible(
                    nombre, 'Febrero 2026', 'S/ 3,500.00'
                )
            elif template == 'cumpleanos':
                message = WhatsAppTemplates.cumpleanos(nombre)
            elif template == 'contrato_por_vencer':
                message = WhatsAppTemplates.contrato_por_vencer(
                    nombre, '15/04/2026', 30
                )
            else:
                message = f"Plantilla '{template}' no reconocida. Uso: vacacion_aprobada, boleta_disponible, cumpleanos, contrato_por_vencer"

        if not message:
            message = (
                "Mensaje de prueba de Harmoni ERP.\n\n"
                "Si recibiste este mensaje, la integracion de WhatsApp "
                "esta funcionando correctamente.\n\n"
                f"Enviado por: {request.user.get_full_name() or request.user.username}"
            )

        result = WhatsAppService.send_message(phone, message)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'ok': False,
            'detail': 'JSON invalido en el cuerpo de la peticion',
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'detail': f'Error inesperado: {str(e)}',
        }, status=500)


@login_required
@solo_admin
@require_POST
def whatsapp_test_connection(request):
    """Test WhatsApp provider connectivity (no message sent)."""
    result = WhatsAppService.test_connection()
    return JsonResponse(result)


@login_required
@solo_admin
@require_POST
def whatsapp_send_to_employee(request):
    """
    Send a WhatsApp message to a specific employee by their Personal ID.

    POST JSON body:
        personal_id: int (required)
        message: str (optional)
        template: str (optional) — template name
    """
    from personal.models import Personal
    from comunicaciones.services import NotificacionService

    try:
        if request.content_type and 'json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST

        personal_id = data.get('personal_id')
        if not personal_id:
            return JsonResponse({'ok': False, 'detail': 'Se requiere personal_id'}, status=400)

        try:
            personal = Personal.objects.get(pk=personal_id)
        except Personal.DoesNotExist:
            return JsonResponse({'ok': False, 'detail': f'Personal con id={personal_id} no encontrado'}, status=404)

        if not personal.celular:
            return JsonResponse({
                'ok': False,
                'detail': f'{personal.apellidos_nombres} no tiene numero de celular registrado',
            }, status=400)

        message = data.get('message', '').strip()
        template = data.get('template', '').strip()
        nombre = personal.apellidos_nombres.split(',')[0].strip() if personal.apellidos_nombres else 'Colaborador'

        if template:
            if template == 'vacacion_aprobada':
                message = WhatsAppTemplates.vacacion_aprobada(
                    nombre,
                    data.get('fecha_inicio', '---'),
                    data.get('fecha_fin', '---'),
                    int(data.get('dias', 0)),
                )
            elif template == 'boleta_disponible':
                message = WhatsAppTemplates.boleta_disponible(
                    nombre,
                    data.get('periodo', '---'),
                    data.get('monto_neto', '---'),
                )
            elif template == 'cumpleanos':
                message = WhatsAppTemplates.cumpleanos(nombre)
            elif template == 'contrato_por_vencer':
                message = WhatsAppTemplates.contrato_por_vencer(
                    nombre,
                    data.get('fecha_vencimiento', '---'),
                    int(data.get('dias_restantes', 0)),
                )
            else:
                message = WhatsAppTemplates.mensaje_libre(
                    nombre,
                    data.get('asunto', 'Notificacion'),
                    message or 'Sin contenido',
                )

        if not message:
            message = f"Hola {nombre}, este es un mensaje de prueba desde Harmoni ERP."

        # Create notification record and send
        notif = NotificacionService.enviar(
            destinatario=personal,
            asunto=data.get('asunto', 'WhatsApp'),
            cuerpo=f'<p>{message}</p>',
            tipo='WHATSAPP',
        )

        return JsonResponse({
            'ok': notif.estado == 'ENVIADA',
            'detail': notif.error_detalle if notif.estado == 'FALLIDA' else 'Mensaje enviado',
            'notificacion_id': notif.pk,
            'estado': notif.estado,
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'detail': 'JSON invalido'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'detail': str(e)}, status=500)
