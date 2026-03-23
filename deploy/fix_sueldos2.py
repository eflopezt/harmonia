import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from decimal import Decimal
from personal.models import Personal

with open('/app/empleados_activos.json', encoding='utf-8') as f:
    emps = json.load(f)

updated = 0
for emp in emps:
    dni = emp['dni']
    basico = Decimal(str(emp.get('basico', 0) or 0))
    alimentacion = Decimal(str(emp.get('alimentacion', 0) or 0))
    hospedaje = Decimal(str(emp.get('hospedaje', 0) or 0))

    if basico <= 0:
        continue

    p = Personal.objects.filter(nro_doc=dni).first()
    if not p:
        p = Personal.objects.filter(nro_doc=dni.lstrip('0')).first()
    if not p:
        continue

    changed = False
    if p.sueldo_base != basico:
        p.sueldo_base = basico
        changed = True
    if alimentacion > 0 and p.alimentacion_mensual != alimentacion:
        p.alimentacion_mensual = alimentacion
        changed = True
    if hospedaje > 0 and p.viaticos_mensual != hospedaje:
        p.viaticos_mensual = hospedaje
        changed = True

    if changed:
        p.save()
        updated += 1

print(f'Actualizados: {updated}')

# Verificar
cero = Personal.objects.filter(estado='Activo', sueldo_base=0).count()
total = Personal.objects.filter(estado='Activo').count()
print(f'Activos con sueldo=0: {cero}/{total}')

# Algunos ejemplos
for p in Personal.objects.filter(estado='Activo').order_by('?')[:5]:
    print(f'  {p.nro_doc} {p.apellidos_nombres}: sueldo={p.sueldo_base} alim={p.alimentacion_mensual} viat={p.viaticos_mensual}')
