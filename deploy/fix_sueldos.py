import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

import openpyxl
from decimal import Decimal
from personal.models import Personal

# Leer matriz de contratos
wb = openpyxl.load_workbook('/app/matriz_contratos.xlsx', read_only=True, data_only=True)
ws = wb['Matriz contrato Activos']

def safe_decimal(val):
    if not val or val == '-' or str(val).strip() == '':
        return Decimal('0')
    try:
        return Decimal(str(val).strip())
    except:
        return Decimal('0')

# Headers: 1=DNI, 11=BASICO, 12=ALIMENTACION, 13=HOSPEDAJE
updated = 0
not_found = 0
for row in ws.iter_rows(min_row=3, values_only=True):
    dni = str(row[1]).strip() if row[1] else None
    if not dni:
        continue

    basico = safe_decimal(row[11])
    alimentacion = safe_decimal(row[12])
    hospedaje = safe_decimal(row[13])

    # Buscar empleado
    p = Personal.objects.filter(nro_doc=dni).first()
    if not p:
        p = Personal.objects.filter(nro_doc=dni.lstrip('0')).first()
    if not p:
        p = Personal.objects.filter(nro_doc=dni.zfill(8)).first()

    if not p:
        not_found += 1
        continue

    changed = False
    if basico > 0 and p.sueldo_base != basico:
        p.sueldo_base = basico
        changed = True
    if alimentacion > 0 and p.alimentacion_mensual != alimentacion:
        p.alimentacion_mensual = alimentacion
        changed = True

    # Hospedaje va a cond_trabajo_mensual o viaticos_mensual
    if hospedaje > 0 and p.viaticos_mensual != hospedaje:
        p.viaticos_mensual = hospedaje
        changed = True

    if changed:
        p.save()
        updated += 1
        print(f'  {dni} {p.apellidos_nombres}: sueldo={basico} alim={alimentacion} hosp={hospedaje}')

wb.close()
print(f'\nActualizados: {updated}')
print(f'No encontrados: {not_found}')

# Verificar cuantos siguen en 0
cero = Personal.objects.filter(estado='Activo', sueldo_base=0).count()
total = Personal.objects.filter(estado='Activo').count()
print(f'Activos con sueldo=0: {cero}/{total}')
