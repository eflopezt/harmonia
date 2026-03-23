import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal
from asistencia.views.reporte_individual import _build_staff_data, _build_rco_data, _get_papeletas, _render_staff_html, _render_rco_html, _render_pdf, _get_ciclo

inicio, fin = _get_ciclo(2026, 3)

# Test LOCAL STAFF
p = Personal.objects.filter(condicion='LOCAL', estado='Activo').first()
print(f'STAFF LOCAL: {p.nro_doc} {p.apellidos_nombres}')
dias, conteo = _build_staff_data(p, inicio, fin)
ds_count = sum(1 for d in dias if d['codigo'] == 'DS')
print(f'  DS auto-detectados: {ds_count}')
print(f'  Conteo: {conteo}')
papeletas = _get_papeletas(p, inicio, fin)
html = _render_staff_html(p, dias, conteo, papeletas, inicio, fin, 3, 2026)
pdf = _render_pdf(html)
print(f'  PDF: {"OK " + str(len(pdf)) if pdf else "FAILED"}')

# Test FORANEO STAFF
p2 = Personal.objects.filter(condicion='FORANEO', estado='Activo').first()
print(f'\nSTAFF FORANEO: {p2.nro_doc} {p2.apellidos_nombres}')
dias2, conteo2 = _build_staff_data(p2, inicio, fin)
ds2 = sum(1 for d in dias2 if d['codigo'] == 'DS')
print(f'  DS: {ds2} (should be 0 for FORANEO)')
print(f'  Conteo: {conteo2}')
html2 = _render_staff_html(p2, dias2, conteo2, [], inicio, fin, 3, 2026)
pdf2 = _render_pdf(html2)
print(f'  PDF: {"OK " + str(len(pdf2)) if pdf2 else "FAILED"}')

# Test RCO
from asistencia.models import RegistroTareo
rco_pid = RegistroTareo.objects.filter(grupo='RCO', fecha__gte=inicio, personal__isnull=False).values_list('personal_id', flat=True).first()
if rco_pid:
    p3 = Personal.objects.get(id=rco_pid)
    print(f'\nRCO: {p3.nro_doc} {p3.apellidos_nombres} ({p3.condicion})')
    dias3, tot3 = _build_rco_data(p3, inicio, fin)
    print(f'  Totales: {tot3}')
    html3 = _render_rco_html(p3, dias3, tot3, [], inicio, fin, 3, 2026)
    pdf3 = _render_pdf(html3)
    print(f'  PDF: {"OK " + str(len(pdf3)) if pdf3 else "FAILED"}')
else:
    # Use any employee as RCO test
    print('\nNo RCO data for March, testing with staff employee as RCO')
    dias3, tot3 = _build_rco_data(p, inicio, fin)
    html3 = _render_rco_html(p, dias3, tot3, [], inicio, fin, 3, 2026)
    pdf3 = _render_pdf(html3)
    print(f'  PDF: {"OK " + str(len(pdf3)) if pdf3 else "FAILED"}')

print('\nAll tests passed!' if all([pdf, pdf2, pdf3]) else '\nSOME TESTS FAILED!')
