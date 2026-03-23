import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal

# Los 47 que eran RCO en enero/febrero
rco_pids = set(
    RegistroTareo.objects.filter(grupo='RCO', fecha__year=2026, fecha__month__in=[1,2])
    .values_list('personal_id', flat=True).distinct()
)

print(f'Empleados con registros RCO en ene/feb: {len(rco_pids)}')

# Actualizar grupo_tareo
updated = 0
for pid in rco_pids:
    p = Personal.objects.get(id=pid)
    if p.grupo_tareo != 'RCO':
        old = p.grupo_tareo
        p.grupo_tareo = 'RCO'
        p.save()
        updated += 1
        print(f'  {p.nro_doc} {p.apellidos_nombres}: {old} -> RCO')

print(f'\nActualizados: {updated}')

# También actualizar registros de marzo que eran STAFF pero deberian ser RCO
mar_updated = RegistroTareo.objects.filter(
    personal_id__in=rco_pids,
    fecha__year=2026, fecha__month=3,
    grupo='STAFF'
).update(grupo='RCO')
print(f'Registros marzo cambiados a RCO: {mar_updated}')

# Verificar
print('\n=== Marzo actualizado ===')
for g in ['STAFF', 'RCO']:
    c = RegistroTareo.objects.filter(grupo=g, fecha__year=2026, fecha__month=3).count()
    print(f'  {g}: {c}')

print('\n=== grupo_tareo actualizado ===')
for gt in ['STAFF', 'RCO']:
    c = Personal.objects.filter(grupo_tareo=gt, estado='Activo').count()
    print(f'  {gt}: {c}')
