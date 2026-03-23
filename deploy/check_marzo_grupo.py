import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal
from django.db.models import Count

print('=== Marzo 2026 - Registros por grupo ===')
for g in ['STAFF', 'RCO']:
    c = RegistroTareo.objects.filter(grupo=g, fecha__year=2026, fecha__month=3).count()
    personas = RegistroTareo.objects.filter(grupo=g, fecha__year=2026, fecha__month=3).values('personal_id').distinct().count()
    print(f'  {g}: {c} registros, {personas} personas')

print('\n=== Febrero 2026 - Registros por grupo ===')
for g in ['STAFF', 'RCO']:
    c = RegistroTareo.objects.filter(grupo=g, fecha__year=2026, fecha__month=2).count()
    personas = RegistroTareo.objects.filter(grupo=g, fecha__year=2026, fecha__month=2).values('personal_id').distinct().count()
    print(f'  {g}: {c} registros, {personas} personas')

print('\n=== Personal con grupo_tareo configurado ===')
for gt in ['STAFF', 'RCO', '', None]:
    c = Personal.objects.filter(grupo_tareo=gt, estado='Activo').count()
    if c: print(f'  grupo_tareo="{gt}": {c} activos')

print('\n=== Ejemplo: empleados RCO en feb que son STAFF en marzo ===')
rco_feb = set(RegistroTareo.objects.filter(grupo='RCO', fecha__year=2026, fecha__month=2).values_list('personal_id', flat=True).distinct())
staff_mar = set(RegistroTareo.objects.filter(grupo='STAFF', fecha__year=2026, fecha__month=3).values_list('personal_id', flat=True).distinct())
rco_to_staff = rco_feb & staff_mar
rco_still = set(RegistroTareo.objects.filter(grupo='RCO', fecha__year=2026, fecha__month=3).values_list('personal_id', flat=True).distinct())
print(f'  RCO en feb: {len(rco_feb)}')
print(f'  De esos, en marzo como STAFF: {len(rco_to_staff)}')
print(f'  De esos, en marzo como RCO: {len(rco_feb & rco_still)}')

# Fuente de importacion de marzo
print('\n=== Fuente de registros marzo ===')
fuentes = list(RegistroTareo.objects.filter(fecha__year=2026, fecha__month=3).values('fuente_codigo').annotate(c=Count('id')).order_by('-c'))
for f in fuentes:
    print(f"  {f['fuente_codigo']}: {f['c']}")

# Importaciones de marzo
from asistencia.models import TareoImportacion
imports = list(TareoImportacion.objects.filter(periodo_inicio__year=2026, periodo_inicio__month=3).values('tipo', 'archivo_nombre', 'total_registros', 'estado'))
if not imports:
    imports = list(TareoImportacion.objects.order_by('-creado_en')[:5].values('tipo', 'archivo_nombre', 'total_registros', 'estado', 'periodo_inicio'))
print('\n=== Ultimas importaciones ===')
for i in imports:
    print(f"  {i}")
