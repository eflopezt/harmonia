"""
Vistas del módulo Asistencia — Solicitudes de Horas Extra.

DL 728 + DS 007-2002-TR: Las HE son voluntarias.
Si ConfiguracionSistema.he_requiere_solicitud = True, el trabajador o su
jefe debe registrar una solicitud aprobada para que el processor registre
las HE. Sin solicitud, el exceso de horas se ignora.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from asistencia.views._common import solo_admin


@login_required
@solo_admin
def solicitudes_he_view(request):
    from asistencia.models import SolicitudHE, ConfiguracionSistema
    from personal.models import Personal

    anio = int(request.GET.get('anio', date.today().year))
    estado = request.GET.get('estado', '')
    personal_id = request.GET.get('personal', '')

    qs = SolicitudHE.objects.select_related('personal', 'aprobado_por').filter(
        fecha__year=anio
    )
    if estado:
        qs = qs.filter(estado=estado)
    if personal_id:
        qs = qs.filter(personal_id=personal_id)

    config = ConfiguracionSistema.get()
    hoy = date.today()

    from django.db.models import Count as _Count, Sum as _Sum, Q as _Q
    he_stats = qs.aggregate(
        total=_Count('id'),
        pendientes=_Count('id', filter=_Q(estado='PENDIENTE')),
        aprobadas=_Count('id', filter=_Q(estado='APROBADA')),
        total_horas=_Sum('horas_estimadas', filter=_Q(estado='APROBADA')),
    )

    context = {
        'titulo': 'Solicitudes de Horas Extra',
        'solicitudes': qs.order_by('-fecha'),
        'personal_list': Personal.objects.filter(estado='Activo').order_by('apellidos_nombres'),
        'anio_actual': anio,
        'anios': range(hoy.year - 1, hoy.year + 2),
        'estados': SolicitudHE.ESTADO_CHOICES,
        'tipos': SolicitudHE.TIPO_CHOICES,
        'filtro_estado': estado,
        'filtro_personal': personal_id,
        'he_requiere_solicitud': config.he_requiere_solicitud,
        'he_stats': he_stats,
    }
    return render(request, 'asistencia/solicitudes_he.html', context)


@login_required
@solo_admin
@require_POST
def solicitud_he_crear(request):
    from asistencia.models import SolicitudHE
    from personal.models import Personal
    try:
        personal = get_object_or_404(Personal, pk=request.POST['personal_id'])
        s = SolicitudHE.objects.create(
            personal=personal,
            fecha=request.POST['fecha'],
            horas_estimadas=request.POST.get('horas_estimadas', '0') or '0',
            tipo=request.POST.get('tipo', 'PAGABLE'),
            motivo=request.POST.get('motivo', '').strip(),
            estado=request.POST.get('estado', 'PENDIENTE'),
        )
        if s.estado in ('APROBADA',):
            s.aprobado_por = request.user
            s.fecha_aprobacion = date.today()
            s.save()
        return JsonResponse(_solicitud_dict(s))
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@solo_admin
@require_POST
def solicitud_he_editar(request, pk):
    from asistencia.models import SolicitudHE
    s = get_object_or_404(SolicitudHE, pk=pk)
    try:
        fecha_raw = request.POST.get('fecha')
        s.fecha = date.fromisoformat(fecha_raw) if fecha_raw else s.fecha
        s.horas_estimadas = request.POST.get('horas_estimadas', s.horas_estimadas) or '0'
        s.tipo = request.POST.get('tipo', s.tipo)
        s.motivo = request.POST.get('motivo', s.motivo).strip()
        s.observaciones = request.POST.get('observaciones', s.observaciones).strip()

        nuevo_estado = request.POST.get('estado', s.estado)
        if nuevo_estado != s.estado:
            s.estado = nuevo_estado
            if nuevo_estado == 'APROBADA':
                s.aprobado_por = request.user
                s.fecha_aprobacion = date.today()

        s.save()
        return JsonResponse(_solicitud_dict(s))
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@solo_admin
@require_POST
def solicitud_he_eliminar(request, pk):
    from asistencia.models import SolicitudHE
    s = get_object_or_404(SolicitudHE, pk=pk)
    s.delete()
    return JsonResponse({'ok': True})


def _solicitud_dict(s):
    return {
        'ok': True,
        'pk': s.pk,
        'personal_nombre': str(s.personal),
        'fecha': s.fecha.strftime('%Y-%m-%d'),
        'fecha_display': s.fecha.strftime('%d/%m/%Y'),
        'horas_estimadas': str(s.horas_estimadas),
        'tipo': s.tipo,
        'tipo_display': s.get_tipo_display(),
        'motivo': s.motivo,
        'estado': s.estado,
        'estado_display': s.get_estado_display(),
        'observaciones': s.observaciones,
    }
