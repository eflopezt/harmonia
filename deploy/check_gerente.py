import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from personal.models import Personal
from asistencia.models import RegistroTareo
from django.db.models import Count

p = Personal.objects.get(nro_doc='001526140')
print(f'{p.apellidos_nombres}')
print(f'cargo={p.cargo} condicion={p.condicion} grupo_tareo={p.grupo_tareo}')
print(f'fecha_alta={p.fecha_alta}')

for m in [1,2,3]:
    regs = RegistroTareo.objects.filter(personal=p, fecha__year=2026, fecha__month=m)
    total = regs.count()
    codigos = list(regs.values('codigo_dia').annotate(c=Count('id')).order_by('-c'))
    cod_str = ', '.join(f"{c['codigo_dia']}={c['c']}" for c in codigos)
    print(f'  Mes {m}: {total} registros -> {cod_str if cod_str else "SIN DATA"}')

# El gerente no marca reloj? No tiene registros?
print(f'\nTotal registros historicos: {RegistroTareo.objects.filter(personal=p).count()}')
