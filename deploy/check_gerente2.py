import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal

p = Personal.objects.get(nro_doc='001526140')
print(f'{p.apellidos_nombres} condicion={p.condicion}')

# Detalle marzo
regs = RegistroTareo.objects.filter(personal=p, fecha__year=2026, fecha__month=3).order_by('fecha')
for r in regs:
    dow = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'][r.fecha.weekday()]
    print(f"  {r.fecha} {dow}: {r.codigo_dia} (dia_semana={r.dia_semana}, condicion={r.condicion})")

# Las FA que se filtran
print(f'\nFA en domingos LOCAL:')
fas = regs.filter(codigo_dia__in=['FA','F'])
for r in fas:
    dow = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'][r.fecha.weekday()]
    es_dom = r.dia_semana == 6 or r.fecha.weekday() == 6
    es_local = r.condicion in ('LOCAL','LIMA','')
    print(f"  {r.fecha} {dow}: cod={r.codigo_dia} dia_semana_bd={r.dia_semana} weekday={r.fecha.weekday()} es_dom={es_dom} es_local={es_local} -> filtrado={es_dom and es_local}")
