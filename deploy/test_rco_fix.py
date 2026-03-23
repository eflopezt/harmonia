import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal
from asistencia.views.reporte_individual import _build_rco_data, _get_papeletas, _render_rco_html, _render_pdf, _get_ciclo

p = Personal.objects.get(nro_doc='73451822')
print(f'Test: {p.nro_doc} {p.apellidos_nombres}')
inicio, fin = _get_ciclo(2026, 3)
print(f'Ciclo: {inicio} a {fin}')

dias, totales = _build_rco_data(p, inicio, fin)
dias_con = [d for d in dias if d['codigo']]
print(f'Dias total: {len(dias)}, con codigo: {len(dias_con)}')
print(f'Totales: {totales}')

papeletas = _get_papeletas(p, inicio, fin)
html = _render_rco_html(p, dias, totales, papeletas, inicio, fin, 3, 2026)
pdf = _render_pdf(html)
print(f'PDF: {"OK " + str(len(pdf)) if pdf else "FAILED"}')
