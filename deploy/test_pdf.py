import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal
from asistencia.views.reporte_individual import _build_staff_data, _get_papeletas, _render_staff_html, _render_pdf, _get_ciclo

p = Personal.objects.filter(estado='Activo').first()
print(f'Test: {p.nro_doc} {p.apellidos_nombres}')

inicio, fin = _get_ciclo(2026, 3)
dias, conteo = _build_staff_data(p, inicio, fin)
papeletas = _get_papeletas(p, inicio, fin)
html = _render_staff_html(p, dias, conteo, papeletas, inicio, fin, 3, 2026)

# Save HTML for debug
with open('/tmp/test_report.html', 'w') as f:
    f.write(html)
print(f'HTML saved to /tmp/test_report.html ({len(html)} chars)')

# Try PDF
try:
    pdf = _render_pdf(html)
    print(f'PDF: OK size={len(pdf)}' if pdf else 'PDF: FAILED (returned None)')
except Exception as e:
    print(f'PDF ERROR: {e}')
    # Try stripping the table and just rendering paragraphs
    simple = f'<html><head><style>@page{{size:A4 landscape;margin:1cm}}</style></head><body>{html[html.find("<body>")+6:html.find("</body>")]}</body></html>'
    print(f'Trying simplified... len={len(simple)}')
