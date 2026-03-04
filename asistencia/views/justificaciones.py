"""
Vistas admin — Justificaciones de No-Marcaje.

RR.HH. revisa las justificaciones enviadas por los trabajadores desde
el portal y las aprueba o rechaza.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from asistencia.views._common import solo_admin


@login_required
@solo_admin
def justificaciones_view(request):
    from asistencia.models import JustificacionNoMarcaje
    from personal.models import Personal

    anio = int(request.GET.get('anio', date.today().year))
    mes_str = request.GET.get('mes', '')
    estado = request.GET.get('estado', '')
    personal_id = request.GET.get('personal', '')

    qs = JustificacionNoMarcaje.objects.select_related(
        'personal', 'revisado_por'
    ).filter(fecha__year=anio)

    if mes_str:
        qs = qs.filter(fecha__month=int(mes_str))
    if estado:
        qs = qs.filter(estado=estado)
    if personal_id:
        qs = qs.filter(personal_id=personal_id)

    hoy = date.today()
    context = {
        'titulo': 'Justificaciones de No-Marcaje',
        'justificaciones': qs.order_by('-fecha'),
        'personal_list': Personal.objects.filter(estado='Activo').order_by('apellidos_nombres'),
        'anio_actual': anio,
        'anios': range(hoy.year - 1, hoy.year + 2),
        'meses': [
            (1,'Enero'),(2,'Febrero'),(3,'Marzo'),(4,'Abril'),
            (5,'Mayo'),(6,'Junio'),(7,'Julio'),(8,'Agosto'),
            (9,'Septiembre'),(10,'Octubre'),(11,'Noviembre'),(12,'Diciembre'),
        ],
        'filtro_mes': mes_str,
        'filtro_estado': estado,
        'filtro_personal': personal_id,
        'estados': JustificacionNoMarcaje.ESTADO_CHOICES,
        'tipos': JustificacionNoMarcaje.TIPO_CHOICES,
        'pendientes': JustificacionNoMarcaje.objects.filter(estado='PENDIENTE').count(),
    }
    return render(request, 'asistencia/justificaciones.html', context)


@login_required
@solo_admin
@require_POST
def justificacion_revisar(request, pk):
    """Aprobar o rechazar una justificación (con comentario opcional)."""
    from asistencia.models import JustificacionNoMarcaje
    j = get_object_or_404(JustificacionNoMarcaje, pk=pk)
    accion = request.POST.get('accion', '')  # 'APROBADA' | 'RECHAZADA'
    comentario = request.POST.get('comentario', '').strip()

    if accion not in ('APROBADA', 'RECHAZADA'):
        return JsonResponse({'ok': False, 'error': 'Acción inválida.'}, status=400)

    j.estado = accion
    j.revisado_por = request.user
    j.fecha_revision = date.today()
    j.comentario_revisor = comentario
    j.save()
    return JsonResponse(_justificacion_dict(j))


@login_required
@solo_admin
@require_POST
def justificacion_eliminar(request, pk):
    from asistencia.models import JustificacionNoMarcaje
    j = get_object_or_404(JustificacionNoMarcaje, pk=pk)
    j.delete()
    return JsonResponse({'ok': True})


def _justificacion_dict(j):
    return {
        'ok': True,
        'pk': j.pk,
        'personal_nombre': str(j.personal),
        'fecha': j.fecha.strftime('%Y-%m-%d'),
        'fecha_display': j.fecha.strftime('%d/%m/%Y'),
        'tipo': j.tipo,
        'tipo_display': j.get_tipo_display(),
        'motivo': j.motivo,
        'estado': j.estado,
        'estado_display': j.get_estado_display(),
        'revisado_por': str(j.revisado_por) if j.revisado_por else '',
        'comentario_revisor': j.comentario_revisor,
    }
