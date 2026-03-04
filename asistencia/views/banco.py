"""
Vistas del módulo Tareo — Banco de Horas.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone

from asistencia.views._common import solo_admin


# ---------------------------------------------------------------------------
# BANCO DE HORAS (solo STAFF)
# ---------------------------------------------------------------------------

@login_required
@solo_admin
def banco_horas_view(request):
    """Saldo del banco de horas acumulativas por personal STAFF."""
    from asistencia.models import BancoHoras

    anio = request.GET.get('anio', timezone.now().year)
    try:
        anio = int(anio)
    except (ValueError, TypeError):
        anio = timezone.now().year

    mes = request.GET.get('mes', '')
    buscar = request.GET.get('buscar', '').strip()

    qs = BancoHoras.objects.filter(periodo_anio=anio).select_related('personal')

    if mes:
        try:
            qs = qs.filter(periodo_mes=int(mes))
        except (ValueError, TypeError):
            pass

    if buscar:
        qs = qs.filter(
            Q(personal__apellidos_nombres__icontains=buscar) |
            Q(personal__nro_doc__icontains=buscar)
        )

    qs = qs.order_by('-periodo_mes', 'personal__apellidos_nombres')

    totales = qs.aggregate(
        t_acum_25=Sum('he_25_acumuladas'),
        t_acum_35=Sum('he_35_acumuladas'),
        t_acum_100=Sum('he_100_acumuladas'),
        t_compensadas=Sum('he_compensadas'),
        t_saldo=Sum('saldo_horas'),
    )

    anios_disponibles = (
        BancoHoras.objects
        .values_list('periodo_anio', flat=True)
        .distinct()
        .order_by('-periodo_anio')
    )

    MESES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]

    context = {
        'titulo': 'Banco de Horas — STAFF',
        'banco_list': qs,
        'totales': totales,
        'anio_sel': anio,
        'mes_sel': mes,
        'buscar': buscar,
        'anios': anios_disponibles,
        'meses': MESES,
        'total_personas': qs.values('personal').distinct().count(),
    }
    return render(request, 'asistencia/banco_horas.html', context)
