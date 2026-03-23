"""Crear empleados faltantes desde planilla."""
import json, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from datetime import datetime, date
from decimal import Decimal
from personal.models import Personal, Area, SubArea
from empresas.models import Empresa

with open('/app/empleados_faltantes.json', 'r', encoding='utf-8') as f:
    faltantes = json.load(f)

empresa = Empresa.objects.first()
existentes = set(Personal.objects.values_list('nro_doc', flat=True))

# Cache subáreas
subarea_cache = {}
def get_subarea(area_nombre):
    if not area_nombre:
        return None
    area_nombre = area_nombre.strip()
    # Limpiar sufijos de intervención
    base = area_nombre.split('-')[0].strip() if '-' in area_nombre else area_nombre
    if base not in subarea_cache:
        area, _ = Area.objects.get_or_create(nombre=base)
        subarea, _ = SubArea.objects.get_or_create(nombre='General', area=area)
        subarea_cache[base] = subarea
    return subarea_cache[base]

def parse_date(val):
    if not val: return None
    val = str(val).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(val[:10] if len(val) > 10 else val, fmt).date()
        except: continue
    return None

def parse_afp(regimen_str):
    if not regimen_str: return '', 'AFP'
    r = str(regimen_str).upper()
    if 'ONP' in r: return '', 'ONP'
    if 'HABITAT' in r: return 'Habitat', 'AFP'
    if 'INTEGRA' in r: return 'Integra', 'AFP'
    if 'PRIMA' in r: return 'Prima', 'AFP'
    if 'PROFUTURO' in r: return 'Profuturo', 'AFP'
    return '', 'AFP'

creados = 0
ya_existian = 0
errores = []

for emp in faltantes:
    dni = emp['dni'].strip()

    # Verificar si ya existe (con o sin ceros)
    if dni in existentes or dni.lstrip('0') in existentes or dni.zfill(8) in existentes:
        ya_existian += 1
        continue

    nombre = emp['nombre']
    if ',' in nombre:
        apellidos, nombres = nombre.split(',', 1)
        parts = apellidos.strip().split()
        ap_pat = parts[0] if parts else ''
        ap_mat = ' '.join(parts[1:]) if len(parts) > 1 else ''
        nombres = nombres.strip()
    else:
        parts = nombre.split()
        ap_pat = parts[0] if len(parts) > 0 else ''
        ap_mat = parts[1] if len(parts) > 1 else ''
        nombres = ' '.join(parts[2:]) if len(parts) > 2 else ''

    fecha_ing = parse_date(emp['fecha_ingreso'])
    fecha_cese = parse_date(emp['fecha_cese'])
    afp_nombre, regimen = parse_afp(emp['regimen_pension'])
    subarea = get_subarea(emp['area'])

    estado = 'Cesado' if fecha_cese else 'Activo'

    try:
        p = Personal.objects.create(
            nro_doc=dni,
            tipo_doc='DNI' if len(dni) <= 8 else 'CE',
            apellidos_nombres=f"{ap_pat} {ap_mat}, {nombres}",
            cargo=emp['cargo'] or 'Sin asignar',
            subarea=subarea,
            fecha_alta=fecha_ing,
            fecha_inicio_contrato=fecha_ing,
            fecha_cese=fecha_cese if fecha_cese else None,
            fecha_fin_contrato=fecha_cese if fecha_cese else None,
            estado=estado,
            motivo_cese='TERMINO DE CONTRATO' if fecha_cese else '',
            empresa=empresa,
            cuspp=emp.get('cuspp', ''),
            afp=afp_nombre,
            regimen_pension=regimen,
            tipo_contrato='PLAZO_FIJO',
            tipo_trab='Empleado',
            codigo_fotocheck=emp.get('codigo', ''),
            sueldo_base=Decimal('0'),
        )
        creados += 1
        existentes.add(dni)
    except Exception as e:
        errores.append(f"{dni} {nombre}: {e}")

print(f'Creados: {creados}')
print(f'Ya existían: {ya_existian}')
print(f'Errores: {len(errores)}')
for e in errores:
    print(f'  {e}')
print(f'\nTotal Personal en BD: {Personal.objects.count()}')
print(f'  Activos: {Personal.objects.filter(estado="Activo").count()}')
print(f'  Cesados: {Personal.objects.filter(estado="Cesado").count()}')
