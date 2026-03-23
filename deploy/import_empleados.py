"""Script para importar empleados desde JSON."""
import json
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from datetime import datetime
from decimal import Decimal
from personal.models import Personal, Area, SubArea
from empresas.models import Empresa

with open('/app/empleados_activos.json', 'r', encoding='utf-8') as f:
    empleados = json.load(f)

empresa = Empresa.objects.first()

# Cache de áreas y subáreas
area_cache = {}
subarea_cache = {}

def get_or_create_subarea(area_nombre):
    """Crea Area y SubArea 'General' para cada área."""
    if not area_nombre:
        return None
    area_nombre = area_nombre.strip()
    if area_nombre not in subarea_cache:
        area, _ = Area.objects.get_or_create(nombre=area_nombre)
        subarea, _ = SubArea.objects.get_or_create(
            nombre='General',
            area=area,
        )
        subarea_cache[area_nombre] = subarea
    return subarea_cache[area_nombre]

CONDICION_MAP = {
    'LOCAL': 'LOCAL',
    'FORANEO': 'FORANEO',
    'LIMA': 'LIMA',
}

creados = 0
actualizados = 0
errores = []

for emp in empleados:
    try:
        subarea = get_or_create_subarea(emp['area'])

        fecha_alta = None
        if emp['fecha_ingreso']:
            fecha_alta = datetime.strptime(emp['fecha_ingreso'], '%Y-%m-%d').date()

        fecha_nac = None
        if emp['fecha_nac']:
            fecha_nac = datetime.strptime(emp['fecha_nac'], '%Y-%m-%d').date()

        fecha_fin = None
        prorroga = emp.get('ultima_prorroga', '') or emp.get('termino_contrato', '')
        if prorroga:
            fecha_fin = datetime.strptime(prorroga, '%Y-%m-%d').date()

        sexo = 'M' if emp['genero'] == 'Masculino' else 'F' if emp['genero'] == 'Femenino' else ''

        # Normalizar condición
        cond_raw = emp.get('condicion', '').strip().upper()
        # Limpiar caracteres raros
        for k, v in CONDICION_MAP.items():
            if k in cond_raw:
                cond_raw = v
                break
        if cond_raw not in CONDICION_MAP.values():
            cond_raw = 'LOCAL'

        correo = emp.get('correo', '')
        if '@' not in correo:
            correo = ''

        # Nombre completo: "APELLIDO_PAT APELLIDO_MAT, NOMBRES"
        nombre_completo = f"{emp['ap_pat']} {emp['ap_mat']}, {emp['nombres']}"

        sueldo = Decimal(str(emp['basico'])) if emp['basico'] else Decimal('0')
        alimentacion = Decimal(str(emp.get('alimentacion', 0) or 0))

        p, created = Personal.objects.update_or_create(
            nro_doc=emp['dni'],
            defaults={
                'tipo_doc': emp['tipo_doc'] or 'DNI',
                'apellidos_nombres': nombre_completo,
                'fecha_nacimiento': fecha_nac,
                'sexo': sexo,
                'celular': emp['celular'],
                'correo_personal': correo,
                'direccion': emp.get('direccion', ''),
                'cargo': emp['cargo'] or 'Sin asignar',
                'subarea': subarea,
                'tipo_trab': emp.get('tipo_trabajador', 'Empleado') or 'Empleado',
                'sueldo_base': sueldo,
                'alimentacion_mensual': alimentacion,
                'condicion': cond_raw,
                'tipo_contrato': 'PLAZO_FIJO',
                'fecha_alta': fecha_alta,
                'fecha_inicio_contrato': fecha_alta,
                'fecha_fin_contrato': fecha_fin,
                'estado': 'Activo',
                'empresa': empresa,
                'codigo_fotocheck': emp.get('codigo_fotocheck', ''),
            }
        )
        if created:
            creados += 1
        else:
            actualizados += 1
    except Exception as e:
        errores.append(f"{emp['dni']} {emp.get('ap_pat','')}: {e}")

print(f'Creados: {creados}')
print(f'Actualizados: {actualizados}')
print(f'Total en BD: {Personal.objects.count()}')
print(f'Errores: {len(errores)}')
for e in errores:
    print(f'  ERROR: {e}')
print(f'\nÁreas: {Area.objects.count()}')
for a in Area.objects.all().order_by('nombre'):
    c = Personal.objects.filter(subarea__area=a).count()
    print(f'  {a.nombre}: {c}')
