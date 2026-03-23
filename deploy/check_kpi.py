import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from asistencia.models import RegistroTareo
from django.db.models import Count
from datetime import date

# Códigos usados
print('Códigos de tareo:')
codigos = RegistroTareo.objects.values('codigo_dia').annotate(c=Count('id')).order_by('-c')
for c in codigos:
    print(f"  {c['codigo_dia']}: {c['c']}")

# KPI del widget
hoy = date.today()
inicio_mes = hoy.replace(day=1)
from personal.models import Personal
activos = Personal.objects.filter(estado='Activo')
tareo = RegistroTareo.objects.filter(
    fecha__gte=inicio_mes, fecha__lte=hoy, personal__in=activos
)
total = tareo.count()
presentes = tareo.filter(codigo_dia__in=['T', 'NOR', 'TR', 'SS']).count()
pct = round(presentes / total * 100, 1) if total else 0
print(f'\nWidget asistencia mes actual ({inicio_mes} a {hoy}):')
print(f'  Total registros: {total}')
print(f'  Presentes (T/NOR/TR/SS): {presentes}')
print(f'  Tasa: {pct}%')

# KPI asistencia view
from asistencia.views.kpis import *
print(f'\nCódigos de presencia usados en vista: T, NOR, TR')
nor_count = tareo.filter(codigo_dia='NOR').count()
dl_count = tareo.filter(codigo_dia='DL').count()
f_count = tareo.filter(codigo_dia='F').count()
vac_count = tareo.filter(codigo_dia='VAC').count()
print(f'  NOR: {nor_count}, DL: {dl_count}, F: {f_count}, VAC: {vac_count}')
