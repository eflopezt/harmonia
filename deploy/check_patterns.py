import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from asistencia.models import RegistroTareo
from django.db.models import Count, Avg
from datetime import date

print('=== Codigos por condicion ENERO ===')
for cond in ['LOCAL', 'FORANEO', 'LIMA']:
    codigos = list(RegistroTareo.objects.filter(
        condicion=cond, fecha__year=2026, fecha__month=1
    ).values('codigo_dia').annotate(c=Count('id')).order_by('-c'))
    if codigos:
        print(f'\n{cond}:')
        for c in codigos:
            print(f"  {c['codigo_dia']}: {c['c']}")

print('\n=== Sabados LOCAL enero (horas) ===')
sabs = list(RegistroTareo.objects.filter(
    condicion='LOCAL', fecha__year=2026, fecha__month=1, dia_semana=5
).values('codigo_dia').annotate(c=Count('id'), avg_h=Avg('horas_normales')).order_by('-c'))
for s in sabs:
    print(f"  {s['codigo_dia']}: count={s['c']} avg_hrs={s['avg_h']}")

print('\n=== Domingos FORANEO enero ===')
doms = list(RegistroTareo.objects.filter(
    condicion='FORANEO', fecha__year=2026, fecha__month=1, dia_semana=6
).values('codigo_dia').annotate(c=Count('id'), avg_h=Avg('horas_normales')).order_by('-c'))
for d in doms:
    print(f"  {d['codigo_dia']}: count={d['c']} avg_hrs={d['avg_h']}")

print('\n=== Sabados FORANEO enero ===')
sabs2 = list(RegistroTareo.objects.filter(
    condicion='FORANEO', fecha__year=2026, fecha__month=1, dia_semana=5
).values('codigo_dia').annotate(c=Count('id'), avg_h=Avg('horas_normales')).order_by('-c'))
for s in sabs2:
    print(f"  {s['codigo_dia']}: count={s['c']} avg_hrs={s['avg_h']}")

# Un ejemplo de LOCAL sabado
print('\n=== Ejemplo LOCAL un sabado ===')
ej = RegistroTareo.objects.filter(
    condicion='LOCAL', fecha__year=2026, fecha__month=1, dia_semana=5, codigo_dia='NOR'
).first()
if ej:
    print(f"  {ej.dni} {ej.fecha} cod={ej.codigo_dia} hrs_norm={ej.horas_normales} hrs_efec={ej.horas_efectivas}")

# Horario: LOCAL trabaja L-V 8.5h + Sabado 5.5h (media jornada)
# FORANEO trabaja L-S 8.5h + Domingo 4h
print('\n=== Patron semanal LOCAL (dias de semana, promedio hrs normales) ===')
for dow in range(7):
    avg = RegistroTareo.objects.filter(
        condicion='LOCAL', fecha__year=2026, fecha__month=1, dia_semana=dow,
        codigo_dia__in=['NOR', 'A', 'T']
    ).aggregate(avg=Avg('horas_normales'))
    dias_sem = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom']
    print(f"  {dias_sem[dow]}: avg={avg['avg']}")
