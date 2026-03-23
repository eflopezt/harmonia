import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
import io
from xhtml2pdf import pisa
from personal.models import Personal
from asistencia.views.reporte_individual import (
    _build_staff_data, _get_papeletas, _get_ciclo, _group_weeks,
    _header, _resumen_staff, _papeletas_sec, _firma, _footer, CSS, CODE_COLORS
)

p = Personal.objects.get(nro_doc='47281542')
inicio, fin = _get_ciclo(2026, 3)
dias, conteo = _build_staff_data(p, inicio, fin)
pap = _get_papeletas(p, inicio, fin)

# Test each component
def test_html(name, html):
    full = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{html}</body></html>'
    buf = io.BytesIO()
    try:
        r = pisa.CreatePDF(io.StringIO(full), dest=buf)
        print(f'{name}: OK={not r.err} size={len(buf.getvalue())}')
    except Exception as e:
        print(f'{name}: ERROR {type(e).__name__}: {str(e)[:80]}')

test_html('header', _header(p, inicio, fin, 3, 2026, 'STAFF'))
test_html('resumen', _resumen_staff(conteo))
test_html('papeletas', _papeletas_sec(pap))
test_html('firma', _firma())
test_html('footer', _footer())

# Test calendar grid
semanas = _group_weeks(dias)
hdr = '<tr>'
for i, ds in enumerate(['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']):
    bg = '#475569' if i < 5 else '#334155' if i == 5 else '#1e293b'
    hdr += f'<td style="background-color:{bg};color:white;font-weight:bold;padding:5px 8px;font-size:7pt">{ds}</td>'
hdr += '</tr>'

weeks = ''
for sem in semanas:
    frow = '<tr>'
    crow = '<tr>'
    for i, cell in enumerate(sem):
        bg_f = '#edf2f7' if i < 5 else '#e2e8f0'
        if cell:
            frow += f'<td style="background-color:{bg_f};font-size:7pt;font-weight:bold;padding:2px 4px;border:1px solid #cbd5e0;text-decoration:underline">{cell["fecha"].strftime("%d/%m")}</td>'
            bg_c = CODE_COLORS.get(cell['codigo'], '#f7fafc')
            crow += f'<td style="background-color:{bg_c};font-size:13pt;font-weight:bold;padding:6px 4px;border:1px solid #cbd5e0">{cell["display"] or "-"}</td>'
        else:
            frow += f'<td style="background-color:#f1f5f9;padding:2px 4px;border:1px solid #e2e8f0">&nbsp;</td>'
            crow += '<td style="background-color:#f1f5f9;padding:6px 4px;border:1px solid #e2e8f0">&nbsp;</td>'
    frow += '</tr>'
    crow += '</tr>'
    weeks += frow + crow

cal_html = f'<table>{hdr}{weeks}</table>'
test_html('calendar', cal_html)

# All together
all_html = _header(p, inicio, fin, 3, 2026, 'STAFF') + _resumen_staff(conteo) + cal_html + _firma() + _footer()
test_html('ALL', all_html)
