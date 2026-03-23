import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal
from asistencia.views.reporte_individual import _build_rco_data, _get_papeletas, _render_rco_html, _render_pdf, _get_ciclo

p = Personal.objects.get(nro_doc='03689683')
inicio, fin = _get_ciclo(2026, 2)
dias, totales = _build_rco_data(p, inicio, fin)
papeletas = _get_papeletas(p, inicio, fin)
html = _render_rco_html(p, dias, totales, papeletas, inicio, fin, 2, 2026)

# Count weeks
weeks = 0
import re
weeks = html.count('padding:1px;border:none')  # separators
print(f'Semanas en HTML: {weeks // 28 if weeks else 0}')

# Count data rows
data_rows = html.count('f0fff4')  # green normal hour cells
print(f'Celdas normales verdes: {data_rows}')

# Count total TDs
tds = html.count('<td')
print(f'Total TDs: {tds}')

# Save and render
with open('/tmp/rco_test.html', 'w') as f:
    f.write(html)
print(f'HTML saved: {len(html)} chars')

pdf = _render_pdf(html)
print(f'PDF: {"OK "+str(len(pdf)) if pdf else "FAILED"}')

# Verify day grouping
print(f'\nDias: {len(dias)}')
# Check semana grouping
sem_count = 0
sem = [None]*7
for d in dias:
    dow = d['fecha'].weekday()
    sem[dow] = d
    if dow == 6:
        sem_count += 1
        days_in_sem = sum(1 for s in sem if s is not None)
        print(f'  Semana {sem_count}: {days_in_sem} dias ({sem[0]["fecha"] if sem[0] else "?"} a {sem[6]["fecha"] if sem[6] else "?"})')
        sem = [None]*7
if any(s is not None for s in sem):
    sem_count += 1
    days_in_sem = sum(1 for s in sem if s is not None)
    print(f'  Semana {sem_count}: {days_in_sem} dias (parcial)')
print(f'Total semanas: {sem_count}')
