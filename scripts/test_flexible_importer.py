"""
Simulacion de importacion para los 3 formatos reales.
Ejecutar con: D:\Harmoni\.venv\Scripts\python.exe scripts\test_flexible_importer.py

Simula exactamente las columnas de los 3 archivos Excel reales:
  1. Asistencia_SegunFechas.xlsx        → WIDE
  2. Asistencia_Detalle_Consorcio.xlsx  → TRANSACCIONAL
  3. PermisosLicencias_Personal.xlsx    → PAPELETAS
"""
import sys
import os
from datetime import date, datetime
from io import BytesIO

# Forzar UTF-8 en Windows (cp1252 no soporta caracteres especiales)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el proyecto al path
sys.path.insert(0, r'D:\Harmoni')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import pandas as pd
from openpyxl import Workbook

# Importar el parser despues de setup de Django
from asistencia.services.flexible_importer import (
    FlexibleAttendanceParser,
    detectar_formato,
    _map_columns,
    _normalize_col,
    FORMAT_WIDE, FORMAT_TRANSACCIONAL, FORMAT_PAPELETAS,
)

# ─────────────────────────────────────────────────────────────
# Colores ANSI
# ─────────────────────────────────────────────────────────────
GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

def header(txt):
    print(f'\n{BOLD}{CYAN}{"="*60}{RESET}')
    print(f'{BOLD}{CYAN}  {txt}{RESET}')
    print(f'{BOLD}{CYAN}{"="*60}{RESET}')

def ok(txt):   print(f'  {GREEN}[OK] {txt}{RESET}')
def warn(txt): print(f'  {YELLOW}[WARN] {txt}{RESET}')
def err(txt):  print(f'  {RED}[ERR] {txt}{RESET}')
def info(txt): print(f'  {txt}')


# ─────────────────────────────────────────────────────────────
# HELPERS: crear Excel en memoria
# ─────────────────────────────────────────────────────────────

def df_to_excel_buffer(sheets: dict[str, pd.DataFrame]) -> BytesIO:
    """Convierte un dict {hoja: df} a BytesIO con openpyxl."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for sheet, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────
# ARCHIVO 1: WIDE  (Asistencia_SegunFechas.xlsx)
# Columnas reales del archivo:
#   DNI | Nombre Completo | Celular | Fecha Ingreso | Partida |
#   Condicion | Tipo Trabajador | Area | Cargo | Mar-1…Mar-31
# Valores típicos: 9.5, 8.0, SS, FA, V, B, CHE, DM, TR, LCG
# ─────────────────────────────────────────────────────────────

def crear_archivo_wide():
    header("ARCHIVO 1 — WIDE  (Asistencia_SegunFechas.xlsx)")

    # Columnas meta
    meta_cols = [
        'DNI', 'Nombre Completo', 'Celular', 'Fecha Ingreso',
        'Partida', 'Condicion', 'Tipo Trabajador', 'Area', 'Cargo',
    ]
    # Columnas fecha (7 dias de marzo 2026)
    fecha_cols = [f'Mar-{d}' for d in range(1, 8)]

    data = [
        # DNI normal (8 dig), FORANEO, STAFF
        ['12345678', 'GARCIA LOPEZ Juan',    '987654321', '2020-01-15',
         'FORANEO', 'FORANEO', 'STAFF', 'OPERACIONES', 'SUPERVISOR',
         9.5, 9.5, 'SS', 9.5, 9.5, 'V', 'B'],
        # DNI con cero inicial (Excel lo guarda como 7 dig)
        [1234567,   'RAMIREZ SILVA Maria',   '912345678', '2021-03-10',
         'LIMA',    'LIMA',    'RCO',   'RRHH',         'ANALISTA',
         8.0, 8.0, 8.0, 'FA', 8.0, 8.0, 8.0],
        # Tercer empleado - permisos mix
        ['87654321', 'TORRES QUISPE Carlos', '999888777', '2019-06-01',
         'LOCAL',   'LOCAL',   'STAFF', 'LOGISTICA',    'ASISTENTE',
         'CHE', 8.5, 8.5, 8.5, 'DM', 8.5, 8.5],
        # Fila vacía / encabezado duplicado (debe ignorarse)
        ['DNI',     '',                      '',           '',
         '',        '',        '',      '',               '',
         '',        '',        '',        '',   '',  '',  ''],
        # DNI solo texto (advertencia)
        ['ABC123',  'INVALIDO Test',          '',           '',
         '',        '',        '',      '',               '',
         8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
    ]

    df = pd.DataFrame(data, columns=meta_cols + fecha_cols)

    print(f'\n  Columnas ({len(df.columns)}):')
    info(f'    {list(df.columns)}')
    print(f'  Filas de datos: {len(df)}')

    # Deteccion anticipada
    fmt = detectar_formato(df)
    print(f'  Formato detectado: {BOLD}{fmt}{RESET}')
    assert fmt == FORMAT_WIDE, f"Esperado WIDE, obtenido {fmt}"
    ok("Formato detectado correctamente como WIDE")

    # Verificar col_map
    col_map = _map_columns(list(df.columns))
    print(f'\n  Mapeo de columnas:')
    for k, v in col_map.items():
        info(f'    {k:20s} → "{v}"')

    # Verificar que FechaIngreso NO se mapea a ingreso
    assert 'ingreso' not in col_map or 'Fecha' not in col_map.get('ingreso', ''), \
        f"BUG: 'Fecha Ingreso' mapeado a campo 'ingreso'! col_map={col_map}"
    ok("FechaIngreso NO se confunde con campo 'ingreso' (bug fix verificado)")

    # Parsear via FlexibleAttendanceParser
    buf = df_to_excel_buffer({'Asistencia': df})
    parser = FlexibleAttendanceParser(buf)
    resultado = parser.parse_todo()

    # Analisis de resultados
    regs = resultado['registros']
    advs = resultado['advertencias']
    errs = resultado['errores']

    print(f'\n  Resultados de parseo:')
    info(f'    Hojas detectadas: {resultado["hojas"]}')
    info(f'    Fechas detectadas: {resultado["fechas"]}')
    info(f'    Total registros: {len(regs)}')
    info(f'    Advertencias: {len(advs)}')
    info(f'    Errores: {len(errs)}')

    # Esperamos: 3 empleados validos × 7 dias = 21 registros
    # (la fila con DNI='DNI' y 'ABC123' se omiten)
    assert len(regs) == 21, f"Esperado 21 registros, obtenidos {len(regs)}"
    ok(f"21 registros parseados correctamente (3 empleados × 7 días)")

    # Verificar DNI zero-padding
    dnis = {r['dni'] for r in regs}
    assert '01234567' in dnis, f"DNI zero-padding fallido! DNIs: {dnis}"
    ok("DNI 1234567 → 01234567 (zero-padding correcto)")

    # Verificar codigos correctos
    codigos = [(r['dni'], r['fecha'].day, r['codigo'], r['horas']) for r in regs]
    # Garcia: día 3 debe ser SS
    ss_regs = [r for r in regs if r['codigo'] == 'SS' and r['dni'] == '12345678']
    assert len(ss_regs) == 1 and ss_regs[0]['fecha'].day == 3, \
        f"SS no detectado para Garcia día 3. Registros SS: {ss_regs}"
    ok("Código SS parseado correctamente")

    # Torres: día 1 debe ser CHE
    che_regs = [r for r in regs if r['codigo'] == 'CHE' and r['dni'] == '87654321']
    assert len(che_regs) == 1 and che_regs[0]['fecha'].day == 1, \
        f"CHE no detectado correctamente"
    ok("Código CHE parseado correctamente")

    # Advertencias esperadas: ABC123 (DNI no numérico)
    assert any('ABC123' in a for a in advs), f"Advertencia DNI ABC123 no generada: {advs}"
    ok("Advertencia por DNI no numérico generada correctamente")

    for a in advs: warn(a)
    for e in errs: err(e)

    print(f'\n  Muestra de registros (primeros 5):')
    for r in regs[:5]:
        info(f'    DNI={r["dni"]} | {r["fecha"]} | cod={r["codigo"]} | h={r["horas"]} | {r["nombre"][:20]}')

    ok("ARCHIVO 1 (WIDE) → PASÓ TODAS LAS VERIFICACIONES")
    return True


# ─────────────────────────────────────────────────────────────
# ARCHIVO 2: TRANSACCIONAL (Asistencia_Detalle_Consorcio.xlsx)
# Columnas reales:
#   DNI | Personal | Celular | FechaIngreso | Condicion |
#   TipoTrabajador | Area | Cargo | Lugar Trabajo |
#   Fecha | Ingreso | Refrigerio | FinRefrigerio | Salida
# ─────────────────────────────────────────────────────────────

def crear_archivo_transaccional():
    header("ARCHIVO 2 — TRANSACCIONAL  (Asistencia_Detalle_Consorcio.xlsx)")

    cols = [
        'DNI', 'Personal', 'Celular', 'FechaIngreso', 'Condicion',
        'TipoTrabajador', 'Area', 'Cargo', 'Lugar Trabajo',
        'Fecha', 'Ingreso', 'Refrigerio', 'FinRefrigerio', 'Salida',
    ]

    # FechaIngreso = fecha de contratacion (datetime completo como lo exporta el sistema)
    fecha_contrato = datetime(2020, 3, 15, 0, 0, 0)

    data = [
        # Dia normal: 8h jornada
        ['12345678', 'GARCIA LOPEZ Juan',  '987', fecha_contrato, 'FORANEO',
         'STAFF', 'OPERACIONES', 'SUPERVISOR', 'PLANTA 1',
         date(2026, 3, 1), '08:00', '13:00', '14:00', '17:30'],
        # Día con HE (salida a las 20:00)
        ['12345678', 'GARCIA LOPEZ Juan',  '987', fecha_contrato, 'FORANEO',
         'STAFF', 'OPERACIONES', 'SUPERVISOR', 'PLANTA 1',
         date(2026, 3, 2), '08:00', '13:00', '14:00', '20:00'],
        # SS: solo ingreso, sin salida
        ['12345678', 'GARCIA LOPEZ Juan',  '987', fecha_contrato, 'FORANEO',
         'STAFF', 'OPERACIONES', 'SUPERVISOR', 'PLANTA 1',
         date(2026, 3, 3), '08:00', None, None, None],
        # FA: sin ingreso ni salida
        ['12345678', 'GARCIA LOPEZ Juan',  '987', fecha_contrato, 'FORANEO',
         'STAFF', 'OPERACIONES', 'SUPERVISOR', 'PLANTA 1',
         date(2026, 3, 4), None, None, None, None],
        # DNI con 7 digitos (Excel dropeo el cero)
        [1234567,   'RAMIREZ SILVA Maria', '912', fecha_contrato, 'LIMA',
         'RCO',   'RRHH',         'ANALISTA',   'OFICINA',
         date(2026, 3, 1), '09:00', '13:30', '14:30', '18:00'],
        # Sin refrigerio
        [1234567,   'RAMIREZ SILVA Maria', '912', fecha_contrato, 'LIMA',
         'RCO',   'RRHH',         'ANALISTA',   'OFICINA',
         date(2026, 3, 2), '09:00', None, None, '18:00'],
    ]

    df = pd.DataFrame(data, columns=cols)

    print(f'\n  Columnas ({len(df.columns)}):')
    info(f'    {list(df.columns)}')
    print(f'  Filas de datos: {len(df)}')

    # Deteccion
    fmt = detectar_formato(df)
    print(f'  Formato detectado: {BOLD}{fmt}{RESET}')
    assert fmt == FORMAT_TRANSACCIONAL, f"Esperado TRANSACCIONAL, obtenido {fmt}"
    ok("Formato detectado correctamente como TRANSACCIONAL")

    # Verificar col_map — el bug clave
    col_map = _map_columns(list(df.columns))
    print(f'\n  Mapeo de columnas:')
    for k, v in col_map.items():
        info(f'    {k:20s} → "{v}"')

    # BUG FIX: FechaIngreso NO debe mapear a 'ingreso'
    if 'ingreso' in col_map:
        assert col_map['ingreso'] == 'Ingreso', \
            f"BUG DETECTADO: campo 'ingreso' mapeado a '{col_map['ingreso']}' en lugar de 'Ingreso'"
        ok("'Ingreso' (hora entrada) mapeado correctamente, NO 'FechaIngreso'")
    else:
        warn("Campo 'ingreso' no detectado en col_map")

    # Verificar que 'fecha' no captura FechaIngreso
    if 'fecha' in col_map:
        assert col_map['fecha'] == 'Fecha', \
            f"BUG: 'fecha' mapeado a '{col_map['fecha']}' en lugar de 'Fecha'"
        ok("'Fecha' (asistencia del día) mapeado correctamente, NO 'FechaIngreso'")

    # Parsear
    buf = df_to_excel_buffer({'Detalle': df})
    parser = FlexibleAttendanceParser(buf)
    resultado = parser.parse_todo()

    regs = resultado['registros']
    advs = resultado['advertencias']
    errs = resultado['errores']

    print(f'\n  Resultados de parseo:')
    info(f'    Hojas detectadas: {resultado["hojas"]}')
    info(f'    Fechas detectadas: {resultado["fechas"]}')
    info(f'    Total registros: {len(regs)}')
    info(f'    Advertencias: {len(advs)}')
    info(f'    Errores: {len(errs)}')

    assert len(regs) == 6, f"Esperado 6 registros, obtenidos {len(regs)}"
    ok("6 registros parseados correctamente")

    # Verificar calculo de horas (dia 1 Garcia: 08:00-17:30 con 1h refrig = 8.5h)
    r_garcia_d1 = next((r for r in regs if r['dni'] == '12345678' and r['fecha'].day == 1), None)
    assert r_garcia_d1, "Registro Garcia dia 1 no encontrado"
    assert r_garcia_d1['codigo'] is None, f"Codigo inesperado: {r_garcia_d1['codigo']}"
    # 08:00-17:30 = 9.5h - 1h refrig = 8.5h
    assert float(r_garcia_d1['horas']) == 8.5, \
        f"Horas Garcia dia 1: esperado 8.5, obtenido {r_garcia_d1['horas']}"
    ok(f"Horas Garcia día 1: 08:00-17:30 - 1h refrig = {r_garcia_d1['horas']}h ✓")

    # Día con HE (Garcia día 2: 08:00-20:00 - 1h = 11h)
    r_garcia_d2 = next((r for r in regs if r['dni'] == '12345678' and r['fecha'].day == 2), None)
    assert r_garcia_d2 and float(r_garcia_d2['horas']) == 11.0, \
        f"HE Garcia dia 2: esperado 11.0h, obtenido {r_garcia_d2['horas'] if r_garcia_d2 else 'None'}"
    ok(f"Horas Garcia día 2 (HE): 08:00-20:00 - 1h = {r_garcia_d2['horas']}h ✓")

    # SS y FA
    r_ss = next((r for r in regs if r['dni'] == '12345678' and r['fecha'].day == 3), None)
    assert r_ss and r_ss['codigo'] == 'SS', f"Esperado SS, obtenido {r_ss}"
    ok(f"García día 3 (solo ingreso, sin salida) → SS ✓")

    r_fa = next((r for r in regs if r['dni'] == '12345678' and r['fecha'].day == 4), None)
    assert r_fa and r_fa['codigo'] == 'FA', f"Esperado FA, obtenido {r_fa}"
    ok(f"García día 4 (sin ingreso ni salida) → FA ✓")

    # DNI zero-padding
    dnis = {r['dni'] for r in regs}
    assert '01234567' in dnis, f"DNI zero-padding fallido. DNIs: {dnis}"
    ok("DNI 1234567 → 01234567 (zero-padding en TRANSACCIONAL correcto)")

    # Ramirez sin refrigerio (día 2): 09:00-18:00 = 9.0h exactas
    r_ram_d2 = next((r for r in regs if r['dni'] == '01234567' and r['fecha'].day == 2), None)
    assert r_ram_d2 and float(r_ram_d2['horas']) == 9.0, \
        f"Ramirez dia 2 sin refrig: esperado 9.0h, obtenido {r_ram_d2['horas'] if r_ram_d2 else 'None'}"
    ok(f"Ramirez día 2 (sin refrigerio): 09:00-18:00 = {r_ram_d2['horas']}h ✓")

    for a in advs: warn(a)
    for e in errs: err(e)

    print(f'\n  Muestra de registros:')
    for r in regs:
        info(f'    DNI={r["dni"]} | {r["fecha"]} | cod={str(r["codigo"]):4s} | h={str(r["horas"]):6s} | raw={r["valor_raw"]}')

    ok("ARCHIVO 2 (TRANSACCIONAL) → PASÓ TODAS LAS VERIFICACIONES")
    return True


# ─────────────────────────────────────────────────────────────
# ARCHIVO 3: PAPELETAS (PermisosLicencias_Personal.xlsx)
# Columnas reales:
#   TipoPermiso | DNI | Personal | Area Trabajo | Cargo |
#   Iniciales | FechaInicio | FechaFin | Detalle
# 14 tipos de permiso: B, BA, CDT, CHE, CPF, CT, DM,
#   FR, LCG, LF, LP, LSG, TR, V
# ─────────────────────────────────────────────────────────────

def crear_archivo_papeletas():
    header("ARCHIVO 3 — PAPELETAS  (PermisosLicencias_Personal.xlsx)")

    cols = [
        'TipoPermiso', 'DNI', 'Personal', 'Area Trabajo', 'Cargo',
        'Iniciales', 'FechaInicio', 'FechaFin', 'Detalle',
    ]

    data = [
        ['Vacaciones',          '12345678', 'GARCIA LOPEZ Juan',   'OPERACIONES', 'SUPERVISOR', 'V',
         date(2026, 3, 9), date(2026, 3, 13), 'Vacaciones anuales'],
        ['Descanso Medico',     '12345678', 'GARCIA LOPEZ Juan',   'OPERACIONES', 'SUPERVISOR', 'DM',
         date(2026, 3, 16), date(2026, 3, 17), 'Certificado medico adjunto'],
        ['Bajada',              '87654321', 'TORRES QUISPE Carlos','LOGISTICA',   'ASISTENTE',  'B',
         date(2026, 3, 6), date(2026, 3, 6), 'Dia libre acumulado'],
        ['Licencia con Goce',   1234567,    'RAMIREZ SILVA Maria', 'RRHH',        'ANALISTA',   'LCG',
         date(2026, 3, 5), date(2026, 3, 5), 'Tramite personal'],
        ['Comp. HE',            '11111111', 'FLORES VEGA Pedro',   'TI',          'PROGRAMADOR','CHE',
         date(2026, 3, 7), date(2026, 3, 7), 'Compensacion HE semana anterior'],
        ['Licencia Sin Goce',   '22222222', 'MENDEZ RUIZ Ana',     'VENTAS',      'EJECUTIVA',  'LSG',
         date(2026, 3, 10), date(2026, 3, 12), 'Motivos personales'],
        # DNI con 7 digitos (Excel dropeo el cero)
        ['Trabajo Remoto',      3456789,    'SANCHEZ LIMA Roberto','ADMIN',        'CONTADOR',   'TR',
         date(2026, 3, 2), date(2026, 3, 6), 'Trabajo remoto aprobado'],
        # Fila con fechas invalidas (advertencia)
        ['Vacaciones',          '99999999', 'INVALIDO Test',       'X',           'X',          'V',
         None, None, 'Sin fechas'],
        # Tipo permiso con iniciales no en catalogo (debe generar advertencia pero no error)
        ['Permiso Especial',    '33333333', 'NUEVA Empleada',      'RRHH',        'ASISTENTE',  'FR',
         date(2026, 3, 3), date(2026, 3, 3), 'Permiso sindical'],
    ]

    df = pd.DataFrame(data, columns=cols)

    print(f'\n  Columnas ({len(df.columns)}):')
    info(f'    {list(df.columns)}')
    print(f'  Filas de datos: {len(df)}')

    # Deteccion
    fmt = detectar_formato(df)
    print(f'  Formato detectado: {BOLD}{fmt}{RESET}')
    assert fmt == FORMAT_PAPELETAS, f"Esperado PAPELETAS, obtenido {fmt}"
    ok("Formato detectado correctamente como PAPELETAS")

    # Verificar col_map
    col_map = _map_columns(list(df.columns))
    print(f'\n  Mapeo de columnas:')
    for k, v in col_map.items():
        info(f'    {k:20s} → "{v}"')

    assert 'tipo_permiso' in col_map, f"tipo_permiso no detectado: {col_map}"
    assert 'fecha_inicio' in col_map, f"fecha_inicio no detectado: {col_map}"
    assert 'fecha_fin'    in col_map, f"fecha_fin no detectado: {col_map}"
    ok("Columnas TipoPermiso, FechaInicio, FechaFin detectadas correctamente")

    # Parsear
    buf = df_to_excel_buffer({'Papeletas': df})
    parser = FlexibleAttendanceParser(buf)
    resultado = parser.parse_todo()

    paps = resultado['papeletas']
    advs = resultado['advertencias']
    errs = resultado['errores']

    print(f'\n  Resultados de parseo:')
    info(f'    Hojas detectadas: {resultado["hojas"]}')
    info(f'    Total papeletas: {len(paps)}')
    info(f'    Advertencias: {len(advs)}')
    info(f'    Errores: {len(errs)}')

    # Esperados: 9 filas - 1 con fechas invalidas = 8 papeletas
    assert len(paps) == 8, f"Esperado 8 papeletas, obtenidas {len(paps)}"
    ok("8 papeletas parseadas (1 omitida por fechas inválidas)")

    # Verificar DNI zero-padding
    dnis = {p['dni'] for p in paps}
    assert '01234567' in dnis, f"DNI zero-padding en papeletas fallido! DNIs: {dnis}"
    ok("DNI 1234567 → 01234567 (zero-padding en PAPELETAS correcto)")
    assert '03456789' in dnis, f"DNI 3456789 → 03456789 fallido! DNIs: {dnis}"
    ok("DNI 3456789 → 03456789 (zero-padding en PAPELETAS correcto)")

    # Verificar vacaciones Garcia
    vac_garcia = next((p for p in paps if p['dni'] == '12345678' and p['iniciales'] == 'V'), None)
    assert vac_garcia, "Papeleta vacaciones Garcia no encontrada"
    assert vac_garcia['fecha_inicio'] == date(2026, 3, 9), \
        f"FechaInicio vacaciones incorrecta: {vac_garcia['fecha_inicio']}"
    assert vac_garcia['fecha_fin'] == date(2026, 3, 13), \
        f"FechaFin vacaciones incorrecta: {vac_garcia['fecha_fin']}"
    ok(f"Vacaciones Garcia: {vac_garcia['fecha_inicio']} → {vac_garcia['fecha_fin']} ✓")

    # Advertencia por fechas invalidas
    assert any('99999999' in a or 'invalida' in a.lower() or 'fecha' in a.lower()
               for a in advs), \
        f"Advertencia fechas invalidas no generada: {advs}"
    ok("Advertencia por fechas inválidas generada correctamente")

    for a in advs: warn(a)
    for e in errs: err(e)

    print(f'\n  Muestra de papeletas:')
    for p in paps:
        info(f'    DNI={p["dni"]} | {p["iniciales"]:5s} | {p["fecha_inicio"]} → {p["fecha_fin"]} | {p["tipo_permiso_raw"][:20]}')

    ok("ARCHIVO 3 (PAPELETAS) → PASÓ TODAS LAS VERIFICACIONES")
    return True


# ─────────────────────────────────────────────────────────────
# TEST EXTRA: Inferencia de año
# ─────────────────────────────────────────────────────────────

def test_year_inference():
    header("TEST EXTRA — Inferencia de año (archivo de diciembre importado en marzo)")
    from asistencia.services.flexible_importer import _inferir_anio_columnas, _parse_date_column_year

    # Simular columnas 'Dic-1' a 'Dic-31' (diciembre 2025, importado en marzo 2026)
    # Con el año actual (2026), 'Dic-1' → 2026-12-01 (futuro > 60 días) → inferir 2025
    hoy = date.today()
    print(f'  Hoy: {hoy}')

    # Columnas Dic-1 a Dic-20 parseadas con año actual
    col_fechas = {}
    for i, day in enumerate(range(1, 21)):
        d = _parse_date_column_year(f'Dic-{day}', hoy.year)
        if d:
            col_fechas[i] = d

    print(f'  Fechas con año actual: {sorted(col_fechas.values())[:3]}...')

    anio_corregido = _inferir_anio_columnas(col_fechas)
    print(f'  Año inferido: {anio_corregido}')

    if hoy.month <= 6:
        # En enero-junio, diciembre del año actual es futuro → debe corregir
        assert anio_corregido == hoy.year - 1, \
            f"Inferencia fallida: esperado {hoy.year - 1}, obtenido {anio_corregido}"
        ok(f"Año corregido: {hoy.year} → {anio_corregido} (diciembre histórico detectado)")
    else:
        warn(f"Test de inferencia solo aplica en enero-junio (hoy={hoy})")
        ok(f"Año sin corrección necesaria (diciembre del año actual no es futuro en {hoy.month})")

    ok("TEST Inferencia de año → PASÓ")


# ─────────────────────────────────────────────────────────────
# TEST EXTRA: Columnas merged (celdas combinadas)
# ─────────────────────────────────────────────────────────────

def test_merged_cells():
    header("TEST EXTRA — Merged cells (celdas combinadas verticalmente en WIDE)")

    import numpy as np

    # Excel con celdas combinadas: Area y Cargo en blanco para filas 2-3
    # IMPORTANTE: necesitamos >= _MIN_DATE_COLS (5) columnas fecha para deteccion WIDE
    meta_cols = ['DNI', 'Nombre Completo', 'Area', 'Cargo']
    fecha_cols = ['Mar-1', 'Mar-2', 'Mar-3', 'Mar-4', 'Mar-5']

    data = [
        # Fila 1: todo completo (merged cell "owner")
        ['11111111', 'GARCIA Juan',   'OPERACIONES', 'SUPERVISOR', 9.5, 9.5, 9.5, 9.5, 9.5],
        # Fila 2: Area y Cargo en blanco (Excel los deja NaN por merged cells)
        ['22222222', 'RAMIREZ Maria', None,           None,          8.0, 8.0, 8.0, 8.0, 8.0],
        # Fila 3: igual
        ['33333333', 'TORRES Carlos', None,           None,          'V', 8.0, 8.0, 8.0, 8.0],
    ]

    df = pd.DataFrame(data, columns=meta_cols + fecha_cols)
    print(f'\n  DataFrame antes de ffill:')
    info(f'    Area valores: {list(df["Area"])}')

    # El parser hace ffill internamente — verificar que funciona
    buf = df_to_excel_buffer({'Asistencia': df})
    parser = FlexibleAttendanceParser(buf)
    resultado = parser.parse_todo()
    regs = resultado['registros']

    # Ramirez y Torres deben tener Area='OPERACIONES' (propagada del primero)
    ramirez_regs = [r for r in regs if r['dni'] == '22222222']
    torres_regs  = [r for r in regs if r['dni'] == '33333333']

    assert ramirez_regs, "Registros de Ramirez no encontrados"
    # Nota: en este caso cada empleado tiene su propia fila, por lo que ffill
    # solo aplica cuando MISMA fila tiene merged pero el empleado principal está arriba
    # El ffill copia el valor de la fila anterior hacia abajo
    area_ramirez = ramirez_regs[0]['area']
    area_torres  = torres_regs[0]['area']  if torres_regs else 'N/A'

    info(f'    Area Ramirez (post-ffill): "{area_ramirez}"')
    info(f'    Area Torres  (post-ffill): "{area_torres}"')

    # Si el área de Ramirez fue NaN, ffill lo llena con 'OPERACIONES'
    assert area_ramirez == 'OPERACIONES', \
        f"ffill fallido: Area Ramirez = '{area_ramirez}' (esperado 'OPERACIONES')"
    ok("ffill para merged cells funciona: NaN de Ramirez → 'OPERACIONES'")

    ok("TEST Merged cells → PASÓ")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    resultados = []

    try:
        resultados.append(('WIDE', crear_archivo_wide()))
    except AssertionError as e:
        err(f"FALLÓ: {e}")
        resultados.append(('WIDE', False))
    except Exception as e:
        err(f"ERROR inesperado WIDE: {e}")
        import traceback; traceback.print_exc()
        resultados.append(('WIDE', False))

    try:
        resultados.append(('TRANSACCIONAL', crear_archivo_transaccional()))
    except AssertionError as e:
        err(f"FALLÓ: {e}")
        resultados.append(('TRANSACCIONAL', False))
    except Exception as e:
        err(f"ERROR inesperado TRANSACCIONAL: {e}")
        import traceback; traceback.print_exc()
        resultados.append(('TRANSACCIONAL', False))

    try:
        resultados.append(('PAPELETAS', crear_archivo_papeletas()))
    except AssertionError as e:
        err(f"FALLÓ: {e}")
        resultados.append(('PAPELETAS', False))
    except Exception as e:
        err(f"ERROR inesperado PAPELETAS: {e}")
        import traceback; traceback.print_exc()
        resultados.append(('PAPELETAS', False))

    try:
        test_year_inference()
        resultados.append(('YEAR_INFERENCE', True))
    except Exception as e:
        err(f"FALLÓ year inference: {e}")
        resultados.append(('YEAR_INFERENCE', False))

    try:
        test_merged_cells()
        resultados.append(('MERGED_CELLS', True))
    except AssertionError as e:
        err(f"FALLÓ merged cells: {e}")
        resultados.append(('MERGED_CELLS', False))
    except Exception as e:
        err(f"ERROR merged cells: {e}")
        import traceback; traceback.print_exc()
        resultados.append(('MERGED_CELLS', False))

    # Resumen final
    print(f'\n{BOLD}{"="*60}')
    print(f'  RESUMEN FINAL')
    print(f'{"="*60}{RESET}')
    todos_ok = True
    for nombre, ok_flag in resultados:
        if ok_flag:
            print(f'  {GREEN}✓ {nombre}{RESET}')
        else:
            print(f'  {RED}✗ {nombre}{RESET}')
            todos_ok = False

    if todos_ok:
        print(f'\n{GREEN}{BOLD}  [PASS] TODOS LOS TESTS PASARON{RESET}')
        sys.exit(0)
    else:
        print(f'\n{RED}{BOLD}  [FAIL] ALGUNOS TESTS FALLARON{RESET}')
        sys.exit(1)
