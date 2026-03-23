import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal
from asistencia.models import RegistroTareo
from asistencia.views.reporte_individual import _build_rco_data, _get_papeletas, _render_rco_html, _render_pdf, _get_ciclo

# Find an RCO employee
rco_pid = RegistroTareo.objects.filter(grupo='RCO', personal__isnull=False).values_list('personal_id', flat=True).first()
if rco_pid:
    p = Personal.objects.get(id=rco_pid)
    print(f'RCO Test: {p.nro_doc} {p.apellidos_nombres}')
    inicio, fin = _get_ciclo(2026, 2)
    dias, totales = _build_rco_data(p, inicio, fin)
    papeletas = _get_papeletas(p, inicio, fin)
    html = _render_rco_html(p, dias, totales, papeletas, inicio, fin, 2, 2026)
    pdf = _render_pdf(html)
    print(f'RCO PDF: {"OK size=" + str(len(pdf)) if pdf else "FAILED"}')
else:
    print('No RCO employees found')
