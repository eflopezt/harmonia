import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from personal.models import Personal, Area, SubArea
from asistencia.models import RegistroTareo
from django.db.models import Count, Q
from datetime import date

hoy = date.today()
print(f'Hoy: {hoy} ({hoy.strftime("%A")})')

# Personal stats
activos = Personal.objects.filter(estado='Activo').count()
cesados = Personal.objects.filter(estado='Cesado').count()
print(f'\nPersonal: activos={activos}, cesados={cesados}')

staff = Personal.objects.filter(estado='Activo', grupo_tareo='STAFF').count()
rco = Personal.objects.filter(estado='Activo', grupo_tareo='RCO').count()
print(f'STAFF={staff}, RCO={rco}')

areas = Area.objects.filter(activa=True).count()
subareas = SubArea.objects.filter(activa=True).count()
print(f'Areas={areas}, SubAreas={subareas}')

# Asistencia hoy
tareo_hoy = RegistroTareo.objects.filter(fecha=hoy).count()
print(f'\nRegistros hoy ({hoy}): {tareo_hoy}')

# Asistencia marzo
tareo_mar = RegistroTareo.objects.filter(fecha__year=2026, fecha__month=3)
total_mar = tareo_mar.count()
faltas_mar_raw = tareo_mar.filter(codigo_dia__in=['F', 'FA', 'LSG']).count()
# Faltas excluyendo domingos LOCAL y cesados
from django.db.models import F as DbF
faltas_mar_clean = tareo_mar.filter(
    codigo_dia__in=['F', 'FA', 'LSG']
).exclude(
    condicion__in=['LOCAL', 'LIMA', ''], dia_semana=6
).exclude(
    personal__fecha_cese__isnull=False,
    fecha__gt=DbF('personal__fecha_cese')
).count()

print(f'Marzo total: {total_mar}')
print(f'Faltas marzo RAW: {faltas_mar_raw}')
print(f'Faltas marzo CLEAN (sin dom LOCAL, sin cesados): {faltas_mar_clean}')
print(f'Diferencia: {faltas_mar_raw - faltas_mar_clean} registros de falta eliminados')

# Detalle de faltas en domingos
dom_faltas = tareo_mar.filter(
    codigo_dia__in=['F', 'FA'], dia_semana=6
).count()
cesado_faltas = tareo_mar.filter(
    codigo_dia__in=['F', 'FA'],
    personal__fecha_cese__isnull=False,
    fecha__gt=DbF('personal__fecha_cese')
).count()
print(f'  Domingos LOCAL marcados como falta: {dom_faltas}')
print(f'  Faltas de empleados cesados: {cesado_faltas}')
