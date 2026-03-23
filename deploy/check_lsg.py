import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from django.db.models import Count

regs = RegistroTareo.objects.filter(fecha__year=2026, fecha__month=3, codigo_dia='LSG')
print(f'Total LSG marzo: {regs.count()}')
por_persona = regs.values('personal__apellidos_nombres', 'personal__nro_doc', 'personal__condicion').annotate(c=Count('id')).order_by('-c')
for p in por_persona:
    print(f"  {p['personal__nro_doc']} {p['personal__apellidos_nombres']} ({p['personal__condicion']}): {p['c']} dias")

# Detalle fechas
for r in regs.select_related('personal').order_by('personal__apellidos_nombres', 'fecha'):
    dow = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'][r.fecha.weekday()]
    print(f"    {r.fecha} {dow}: {r.personal.apellidos_nombres if r.personal else r.dni}")

# Tambien enero y febrero
for m in [1, 2]:
    c = RegistroTareo.objects.filter(fecha__year=2026, fecha__month=m, codigo_dia='LSG').count()
    if c:
        print(f'\nLSG mes {m}: {c} registros')
