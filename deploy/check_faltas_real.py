import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from django.db.models import F, Count

print('=== FALTAS REALES MARZO 2026 ===\n')

# Base: todos los registros de marzo
qs = RegistroTareo.objects.filter(fecha__year=2026, fecha__month=3)
print(f'Total registros marzo: {qs.count()}')

# Faltas raw
fa_raw = qs.filter(codigo_dia__in=['FA', 'F']).count()
print(f'FA raw (sin filtro): {fa_raw}')

# Excluir post-cese
fa_sin_postcese = qs.filter(codigo_dia__in=['FA', 'F']).exclude(
    personal__fecha_cese__isnull=False, fecha__gt=F('personal__fecha_cese')
).count()
print(f'FA sin post-cese: {fa_sin_postcese} (eliminadas: {fa_raw - fa_sin_postcese})')

# Excluir pre-ingreso
fa_sin_pre = qs.filter(codigo_dia__in=['FA', 'F']).exclude(
    personal__fecha_cese__isnull=False, fecha__gt=F('personal__fecha_cese')
).exclude(
    personal__fecha_alta__isnull=False, fecha__lt=F('personal__fecha_alta')
).count()
print(f'FA sin post-cese ni pre-ingreso: {fa_sin_pre} (eliminadas: {fa_sin_postcese - fa_sin_pre})')

# Excluir domingos LOCAL
fa_clean = qs.filter(codigo_dia__in=['FA', 'F']).exclude(
    personal__fecha_cese__isnull=False, fecha__gt=F('personal__fecha_cese')
).exclude(
    personal__fecha_alta__isnull=False, fecha__lt=F('personal__fecha_alta')
).exclude(
    condicion__in=['LOCAL', 'LIMA', ''], dia_semana=6
).count()
print(f'FA REAL (final): {fa_clean} (domingos LOCAL eliminados: {fa_sin_pre - fa_clean})')

# Detalle de las faltas reales
print(f'\n=== Detalle faltas reales ({fa_clean}) ===')
faltas = qs.filter(codigo_dia__in=['FA', 'F']).exclude(
    personal__fecha_cese__isnull=False, fecha__gt=F('personal__fecha_cese')
).exclude(
    personal__fecha_alta__isnull=False, fecha__lt=F('personal__fecha_alta')
).exclude(
    condicion__in=['LOCAL', 'LIMA', ''], dia_semana=6
).select_related('personal').order_by('personal__apellidos_nombres', 'fecha')

personas = {}
for r in faltas:
    nombre = r.personal.apellidos_nombres if r.personal else r.dni
    if nombre not in personas:
        personas[nombre] = []
    personas[nombre].append(r.fecha.strftime('%d/%m'))

for nombre, fechas in sorted(personas.items()):
    print(f'  {nombre}: {len(fechas)} faltas -> {", ".join(fechas)}')
