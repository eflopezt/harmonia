"""
Vistas del módulo Tareo — Exportaciones.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect

from asistencia.views._common import solo_admin


# ---------------------------------------------------------------------------
# EXPORTAR CARGA S10
# ---------------------------------------------------------------------------

@login_required
@solo_admin
def exportar_carga_s10_view(request):
    """Genera y descarga el archivo CargaS10 para importar en el sistema S10."""
    from asistencia.services.exporters import CargaS10Exporter

    anio = int(request.GET.get('anio', date.today().year))
    mes = int(request.GET.get('mes', date.today().month))

    try:
        exporter = CargaS10Exporter(anio, mes)
        buffer = exporter.generar()

        MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        filename = f'CargaS10_{MESES[mes-1]}_{anio}.xlsx'

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f'Error generando CargaS10: {e}')
        return redirect('asistencia_dashboard')


# ---------------------------------------------------------------------------
# EXPORTAR REPORTE CIERRE
# ---------------------------------------------------------------------------

@login_required
@solo_admin
def exportar_cierre_view(request):
    """Genera el reporte de cierre de mes."""
    from asistencia.services.exporters import ReporteCierreExporter

    anio = int(request.GET.get('anio', date.today().year))
    mes = int(request.GET.get('mes', date.today().month))

    try:
        exporter = ReporteCierreExporter(anio, mes)
        buffer = exporter.generar()

        MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        filename = f'Cierre_{MESES[mes-1]}_{anio}.xlsx'

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f'Error generando reporte de cierre: {e}')
        return redirect('asistencia_dashboard')
