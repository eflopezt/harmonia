import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal
from datetime import date

p = Personal.objects.get(nro_doc='73451822')
area = p.subarea.area.nombre if p.subarea else '-'
print(f'{p.apellidos_nombres} | grupo_tareo={p.grupo_tareo} | condicion={p.condicion}')
print(f'fecha_alta={p.fecha_alta} | cargo={p.cargo} | area={area}')

for g in ['STAFF','RCO']:
    for m in [1,2,3]:
        c = RegistroTareo.objects.filter(personal=p, grupo=g, fecha__year=2026, fecha__month=m).count()
        if c: print(f'  {g} mes={m}: {c} registros')

print('\nCiclo marzo (21/02 al 20/03):')
regs = list(RegistroTareo.objects.filter(
    personal=p, fecha__gte=date(2026,2,21), fecha__lte=date(2026,3,20)
).order_by('fecha').values('fecha','grupo','codigo_dia','horas_normales','he_25','he_35','he_100'))
for r in regs:
    print(f"  {r['fecha']} {r['grupo']:5} {r['codigo_dia']:4} n={r['horas_normales']} h25={r['he_25']} h35={r['he_35']} h100={r['he_100']}")
print(f'Total: {len(regs)}')
