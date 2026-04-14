"""
Vista global de Reglas Especiales de Asistencia.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from asistencia.models import ReglaEspecialPersonal
from asistencia.views._common import solo_admin


DIAS_NOMBRE = {
    0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 4: 'Vie', 5: 'Sáb', 6: 'Dom',
}


@login_required
@solo_admin
def lista_reglas(request):
    """Vista global de todas las reglas especiales."""
    buscar = request.GET.get('buscar', '').strip()
    estado = request.GET.get('estado', '')

    qs = ReglaEspecialPersonal.objects.select_related('personal', 'creado_por').order_by(
        'personal__apellidos_nombres', 'prioridad')

    if buscar:
        from django.db.models import Q
        qs = qs.filter(
            Q(personal__apellidos_nombres__icontains=buscar)
            | Q(personal__nro_doc__icontains=buscar)
            | Q(descripcion__icontains=buscar)
            | Q(codigo_resultado__icontains=buscar)
        )
    if estado == 'activas':
        qs = qs.filter(activa=True)
    elif estado == 'inactivas':
        qs = qs.filter(activa=False)

    reglas = []
    for r in qs:
        dias_str = ', '.join(DIAS_NOMBRE.get(d, '?') for d in (r.dias_semana or [])) or 'Todos'
        reglas.append({
            'obj': r,
            'dias_str': dias_str,
        })

    context = {
        'titulo': 'Reglas Especiales de Asistencia',
        'reglas': reglas,
        'total': len(reglas),
        'buscar': buscar,
        'estado': estado,
    }
    return render(request, 'asistencia/reglas_especiales.html', context)
