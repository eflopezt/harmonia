import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal
from datetime import date
p = Personal.objects.get(nro_doc='43290334')
print(f'{p.apellidos_nombres} condicion={p.condicion}')
domingos = [date(2026,2,22), date(2026,3,1), date(2026,3,8), date(2026,3,15)]
for dom in domingos:
    regs = list(RegistroTareo.objects.filter(personal=p, fecha=dom).values('grupo','codigo_dia','horas_normales'))
    for r in regs:
        print(f"  {dom} grupo={r['grupo']} cod={r['codigo_dia']} hrs={r['horas_normales']}")
    if not regs:
        print(f"  {dom} SIN REGISTRO")

# Test build
from asistencia.views.reporte_individual import _build_staff_data, _get_ciclo
inicio, fin = _get_ciclo(2026, 3)
dias, conteo = _build_staff_data(p, inicio, fin)
print(f'\nConteo: {conteo}')
for d in dias:
    if d['fecha'].weekday() == 6:
        print(f"  {d['fecha']} Dom: codigo={d['codigo']} display={d['display']}")
