import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from personal.models import Personal
from asistencia.views.reporte_individual import _build_staff_data, _build_rco_data, _get_papeletas, _render_staff_html, _render_rco_html, _render_pdf, _get_ciclo

inicio, fin = _get_ciclo(2026, 3)
for dni in ['47281542', '73451822', '46127028', '43290334']:
    p = Personal.objects.get(nro_doc=dni)
    d, c = _build_staff_data(p, inicio, fin)
    h = _render_staff_html(p, d, c, _get_papeletas(p, inicio, fin), inicio, fin, 3, 2026)
    pdf = _render_pdf(h)
    pages = pdf.count(b'/Type /Page') - pdf.count(b'/Type /Pages')
    print(f'STAFF {dni}: {pages} page(s) ({len(pdf)} bytes)')

    d2, t2 = _build_rco_data(p, inicio, fin)
    h2 = _render_rco_html(p, d2, t2, _get_papeletas(p, inicio, fin), inicio, fin, 3, 2026)
    pdf2 = _render_pdf(h2)
    pages2 = pdf2.count(b'/Type /Page') - pdf2.count(b'/Type /Pages')
    print(f'RCO   {dni}: {pages2} page(s) ({len(pdf2)} bytes)')
