"""Importar papeletas/permisos desde Excel."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

import openpyxl
from datetime import datetime, date
from django.contrib.auth.models import User
from vacaciones.models import SolicitudPermiso, TipoPermiso
from personal.models import Personal

ARCHIVO = sys.argv[1]
admin = User.objects.get(username='admin')

# Cache personal por DNI
personal_cache = {}
for p in Personal.objects.all():
    personal_cache[p.nro_doc] = p
    personal_cache[p.nro_doc.lstrip('0')] = p

# Crear tipos de permiso faltantes
TIPO_MAP = {
    'BAJADAS': 'bajada-dl',
    'BAJADAS ACUMULADAS': 'bajada-dla',
    'VACACIONES': 'vacaciones',
    'COMPENSACION POR HORARIO EXTENDIDO': 'comp-he',
    'COMPENSACIÓN POR FERIADO': 'comp-feriado',
    'COMPENSACIÓN DE DIAS POR TRABAJOS': 'comp-dias',
    'LICENCIA CON GOCE': 'con-goce',
    'LICENCIA SIN GOCE': 'sin-goce',
    'DESCANSO MEDICO': 'descanso-medico',
    'ATENCION MEDICA': 'atencion-medica',
    'LICENCIA POR FALLECIMIENTO': 'fallecimiento',
    'FERIADO NO RECUPERABLE': 'feriado-nr',
    'TRABAJO REMOTO': 'trabajo-remoto',
    'COMISION DE TRABAJO': 'comision-trabajo',
    'SUSPENSIÓN POR ACTO INSEGURO': 'suspension',
    'LICENCIA POR PATERNIDAD': 'paternidad',
    'AMONESTACIÓ POR SUSPENSIÓN': 'amonestacion',
}

# Nombres legibles
TIPO_NOMBRES = {
    'vacaciones': 'Vacaciones',
    'comp-he': 'Compensación por Horario Extendido',
    'comp-feriado': 'Compensación por Feriado',
    'comp-dias': 'Compensación de Días por Trabajo',
    'con-goce': 'Licencia con Goce',
    'atencion-medica': 'Atención Médica',
    'feriado-nr': 'Feriado No Recuperable',
    'trabajo-remoto': 'Trabajo Remoto',
    'comision-trabajo': 'Comisión de Trabajo',
    'suspension': 'Suspensión por Acto Inseguro',
    'amonestacion': 'Amonestación por Suspensión',
}

# Asegurar que todos los tipos existen
tipo_cache = {tp.codigo: tp for tp in TipoPermiso.objects.all()}
for excel_tipo, codigo in TIPO_MAP.items():
    if codigo not in tipo_cache:
        nombre = TIPO_NOMBRES.get(codigo, excel_tipo.title())
        tp = TipoPermiso.objects.create(
            codigo=codigo,
            nombre=nombre,
            pagado=codigo not in ('sin-goce', 'suspension', 'amonestacion'),
        )
        tipo_cache[codigo] = tp
        print(f'Tipo creado: {codigo} - {nombre}')

# Leer Excel
wb = openpyxl.load_workbook(ARCHIVO, read_only=True, data_only=True)
ws = wb['Sheet']

creados = 0
errores = []
duplicados = 0

for row in ws.iter_rows(min_row=2, values_only=True):
    if not row[1]:
        continue

    tipo_excel = str(row[0]).strip() if row[0] else ''
    dni = str(row[1]).strip()
    detalle = str(row[8]).strip() if row[8] else ''

    # Normalizar tipo (quitar acentos raros del Excel)
    tipo_clean = tipo_excel.upper()
    for k in TIPO_MAP:
        # Comparar sin acentos
        k_clean = k.replace('Ó', 'O').replace('É', 'E').replace('Í', 'I')
        t_clean = tipo_clean.replace('\ufffd', 'O').replace('Ó', 'O').replace('É', 'E').replace('Í', 'I')
        if k_clean == t_clean or k == tipo_excel.upper():
            tipo_clean = k
            break

    codigo = TIPO_MAP.get(tipo_clean)
    if not codigo:
        # Fuzzy match
        for k, v in TIPO_MAP.items():
            if k[:10] in tipo_clean or tipo_clean[:10] in k:
                codigo = v
                break
    if not codigo:
        errores.append(f'{dni}: Tipo no mapeado "{tipo_excel}"')
        continue

    tipo_obj = tipo_cache.get(codigo)
    if not tipo_obj:
        errores.append(f'{dni}: Tipo {codigo} no encontrado')
        continue

    personal = personal_cache.get(dni) or personal_cache.get(dni.lstrip('0'))
    if not personal:
        errores.append(f'{dni}: Personal no encontrado')
        continue

    fecha_inicio = None
    fecha_fin = None
    if row[6]:
        if isinstance(row[6], datetime):
            fecha_inicio = row[6].date()
        elif isinstance(row[6], date):
            fecha_inicio = row[6]
    if row[7]:
        if isinstance(row[7], datetime):
            fecha_fin = row[7].date()
        elif isinstance(row[7], date):
            fecha_fin = row[7]

    if not fecha_inicio:
        errores.append(f'{dni}: Sin fecha inicio')
        continue
    if not fecha_fin:
        fecha_fin = fecha_inicio

    dias = (fecha_fin - fecha_inicio).days + 1

    # Verificar duplicado
    exists = SolicitudPermiso.objects.filter(
        personal=personal,
        tipo=tipo_obj,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    ).exists()
    if exists:
        duplicados += 1
        continue

    try:
        SolicitudPermiso.objects.create(
            personal=personal,
            tipo=tipo_obj,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            dias=dias,
            motivo=detalle,
            estado='aprobado',
            solicitado_por=admin,
            aprobado_por=admin,
            fecha_aprobacion=fecha_inicio,
        )
        creados += 1
    except Exception as e:
        errores.append(f'{dni} {fecha_inicio}: {e}')

wb.close()

print(f'\n=== RESULTADO ===')
print(f'Creados: {creados}')
print(f'Duplicados omitidos: {duplicados}')
print(f'Errores: {len(errores)}')
print(f'Total papeletas en BD: {SolicitudPermiso.objects.count()}')
if errores:
    print('\nErrores (primeros 20):')
    for e in errores[:20]:
        print(f'  {e}')
