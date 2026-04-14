"""
Management command: sync_datos_abril_2026
==========================================
Procesa los 3 archivos Excel de abril 2026:
  1. Lista_Personal.xlsx      → crea nuevos empleados + aplica ceses
  2. Asistencia_Detalle_Consorcio.xlsx → importa asistencia abril
  3. PermisosLicencias_Personal.xlsx  → crea papeletas/permisos

Uso:
    python manage.py sync_datos_abril_2026
    python manage.py sync_datos_abril_2026 --dry-run
    python manage.py sync_datos_abril_2026 --solo personal
    python manage.py sync_datos_abril_2026 --solo asistencia
    python manage.py sync_datos_abril_2026 --solo papeletas
"""
from __future__ import annotations

import unicodedata
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# ── Rutas de los archivos ──────────────────────────────────────────────────
import os as _os
BASE_DIR = Path(_os.environ.get('SYNC_BASE_DIR', r"C:\Users\EDWIN LOPEZ\Downloads"))
ARCHIVO_PERSONAL    = BASE_DIR / "Lista_Personal.xlsx"
ARCHIVO_ASISTENCIA  = BASE_DIR / "Asistencia_Detalle_Consorcio.xlsx"
ARCHIVO_PAPELETAS   = BASE_DIR / "PermisosLicencias_Personal.xlsx"

# ── Helpers de normalización ───────────────────────────────────────────────

def _sin_tildes(s: str) -> str:
    """Elimina tildes/diacríticos para comparación robusta."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def _norm_key(s: str) -> str:
    return _sin_tildes(str(s or '')).upper().strip()


# ── Mapeos ─────────────────────────────────────────────────────────────────
MOTIVO_CESE_MAP = {
    'TERMINO DE CONTRATO':                   'TERMINO DE CONTRATO',
    'FIN DE CONTRATO':                       'FIN DE CONTRATO',
    'RENUNCIA VOLUNTARIA':                   'RENUNCIA VOLUNTARIA',
    'POSITIVO ALCOTEST':                     'POSITIVO ALCOTEST',
    'PERIODO DE PRUEBA':                     'PERIODO DE PRUEBA',
    'NO INICIO VINCULO LABORAL':             'NO INICIO VINCULO',
    'RENUNCIA VOLUNTARIA POSITIVO ALCOTEST': 'RENUNCIA-ALCOTEST',
}

# Mapeo clave sin tildes → choice interno
TIPO_PERMISO_MAP = {
    'BAJADAS':                                   'BAJADAS',
    'BAJADA':                                    'BAJADAS',
    'COMPENSACION POR HORARIO EXTENDIDO':        'COMPENSACION_HE',
    'COMPENSACION DE HORARIO EXTENDIDO':         'COMPENSACION_HE',
    'CHE':                                       'COMPENSACION_HE',
    'VACACIONES':                                'VACACIONES',
    'COMPENSACION DE DIAS POR TRABAJOS':         'COMP_DIA_TRABAJO',
    'COMPENSACION DE DIA POR TRABAJO':           'COMP_DIA_TRABAJO',
    'COMPENSACION DE DIAS POR TRABAJO':          'COMP_DIA_TRABAJO',
    'BAJADAS ACUMULADAS':                        'BAJADAS_ACUMULADAS',
    'BAJADA ACUMULADA':                          'BAJADAS_ACUMULADAS',
    'COMISION DE TRABAJO':                       'COMISION_TRABAJO',
    'LICENCIA SIN GOCE':                         'LICENCIA_SIN_GOCE',
    'SUSPENSION POR ACTO INSEGURO':              'SUSPENSION_ACTO_INSEGURO',
    'AMONESTACION POR SUSPENSION':               'SUSPENSION',
    'AMONESTACIO POR SUSPENSION':                'SUSPENSION',  # truncado sin N final
    'TRABAJO REMOTO':                            'TRABAJO_REMOTO',
    'DESCANSO MEDICO':                           'DESCANSO_MEDICO',
    'LICENCIA CON GOCE':                         'LICENCIA_CON_GOCE',
    'LICENCIA POR PATERNIDAD':                   'LICENCIA_PATERNIDAD',
    'LICENCIA POR FALLECIMIENTO':                'LICENCIA_FALLECIMIENTO',
}

INICIALES_CHOICES = {
    'B', 'BA', 'VAC', 'V', 'CHE', 'LSG', 'CDT', 'CMDT',
    'SAI', 'SPA', 'TR', 'TREM', 'DM', 'LCG', 'CT', 'AS',
}

# Jornadas por condición y día de semana (0=Lun … 6=Dom)
JORNADA = {
    'LOCAL':   {0: 8.5, 1: 8.5, 2: 8.5, 3: 8.5, 4: 8.5, 5: 5.5, 6: 0.0},
    'FORANEO': {0: 11.0, 1: 11.0, 2: 11.0, 3: 11.0, 4: 11.0, 5: 11.0, 6: 4.0},
    'LIMA':    {0: 8.5, 1: 8.5, 2: 8.5, 3: 8.5, 4: 8.5, 5: 5.5, 6: 0.0},
}


# ── Utilidades de parseo ───────────────────────────────────────────────────

def _norm_dni(val) -> str:
    if val is None:
        return ''
    s = str(val).strip().split('.')[0]
    return s.zfill(8)


def _norm_condicion(val: str) -> str:
    return _sin_tildes(str(val or '')).upper().strip()


def _parse_fecha(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _parse_hora_str(val) -> str | None:
    """Devuelve 'HH:MM' o None."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ('', 'nan', 'NaT', 'None', 'NaN'):
        return None
    if len(s) >= 5:
        return s[:5]
    return None


def _hora_str_a_time(h) -> time | None:
    import math
    if h is None:
        return None
    if isinstance(h, float) and math.isnan(h):
        return None
    s = str(h).strip()
    if not s or s in ('nan', 'NaN', 'NaT', 'None'):
        return None
    try:
        t = datetime.strptime(s[:5], '%H:%M')
        return t.time()
    except (ValueError, TypeError):
        return None


def _str_hora(val) -> str | None:
    import math
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    return s if s else None


def _calc_horas(ingreso, salida, refrigerio, fin_ref) -> float | None:
    ingreso    = _str_hora(ingreso)
    salida     = _str_hora(salida)
    refrigerio = _str_hora(refrigerio)
    fin_ref    = _str_hora(fin_ref)
    if not ingreso or not salida:
        return None
    fmt = '%H:%M'
    try:
        t_in = datetime.strptime(ingreso, fmt)
        t_out = datetime.strptime(salida, fmt)
        delta = t_out - t_in
        if delta.total_seconds() < 0:
            delta += timedelta(hours=24)
        horas = delta.total_seconds() / 3600
        if refrigerio and fin_ref:
            try:
                r_in = datetime.strptime(refrigerio, fmt)
                r_out = datetime.strptime(fin_ref, fmt)
                ref_d = r_out - r_in
                if ref_d.total_seconds() > 0:
                    horas -= ref_d.total_seconds() / 3600
            except ValueError:
                pass
        return max(round(horas, 2), 0.0)
    except ValueError:
        return None


def _calc_he(horas: float, jornada: float,
             es_feriado: bool, es_domingo_local: bool
             ) -> tuple[float, float, float, float, float]:
    """Retorna (h_efectivas, h_normales, he_25, he_35, he_100)."""
    if es_feriado or es_domingo_local:
        return horas, 0.0, 0.0, 0.0, round(horas, 2)
    if jornada <= 0:
        return horas, 0.0, 0.0, 0.0, round(horas, 2)
    h_norm = min(horas, jornada)
    exceso = max(horas - jornada, 0.0)
    he25 = min(exceso, 2.0)
    he35 = max(exceso - 2.0, 0.0)
    return horas, round(h_norm, 2), round(he25, 2), round(he35, 2), 0.0


class Command(BaseCommand):
    help = 'Sincroniza personal, asistencia y papeletas desde archivos Excel de abril 2026'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Muestra cambios sin guardar nada en BD')
        parser.add_argument('--solo', choices=['personal', 'asistencia', 'papeletas'],
                            help='Ejecutar solo una sección')

    def handle(self, *args, **options):
        try:
            import pandas as pd
        except ImportError:
            raise CommandError('Instalar pandas: pip install pandas openpyxl')

        self.dry = options['dry_run']
        self.solo = options.get('solo')
        self.pd = pd

        if self.dry:
            self.stdout.write('=== MODO DRY-RUN: no se guardara nada ===\n')

        try:
            if not self.solo or self.solo == 'personal':
                self._sync_personal()
            if not self.solo or self.solo == 'asistencia':
                self._sync_asistencia()
            if not self.solo or self.solo == 'papeletas':
                self._sync_papeletas()
        except KeyboardInterrupt:
            self.stdout.write('\nInterrumpido.')
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS('\nProceso completado.'))

    # ══════════════════════════════════════════════════════════════════════
    # 1. PERSONAL
    # ══════════════════════════════════════════════════════════════════════

    def _sync_personal(self):
        from personal.models import Personal, SubArea

        self.stdout.write('\n== [1/3] SINCRONIZACION DE PERSONAL ==')

        pd = self.pd
        df = pd.read_excel(ARCHIVO_PERSONAL, sheet_name='Sheet',
                           dtype={'DNI': str}, engine='openpyxl')
        df['_dni'] = df['DNI'].apply(_norm_dni)

        # Mapa subarea: clave_sin_tildes -> SubArea
        subarea_map: dict[str, 'SubArea'] = {}
        for sa in SubArea.objects.select_related('area').all():
            key = _norm_key(sa.nombre)
            subarea_map[key] = sa
            area_key = _norm_key(sa.area.nombre)
            if area_key not in subarea_map:
                subarea_map[area_key] = sa

        # DNIs en BD
        dnis_bd: dict[str, Personal] = {p.nro_doc: p for p in Personal.objects.all()}

        nuevos = 0
        ceses = 0
        skip_ya_cese = 0
        errores = []

        for _, row in df.iterrows():
            dni = row['_dni']
            nombre = str(row.get('Personal', '')).strip()
            activo = bool(row.get('Estado', True))
            fecha_cese = _parse_fecha(row.get('FechaCese'))
            motivo_raw = _norm_key(row.get('MotivoCese', '') or '')
            motivo = MOTIVO_CESE_MAP.get(motivo_raw, motivo_raw[:20])

            # ── Existente ──────────────────────────────────────────────
            if dni in dnis_bd:
                p = dnis_bd[dni]
                if not activo and fecha_cese:
                    if p.fecha_cese == fecha_cese:
                        skip_ya_cese += 1
                        continue
                    self.stdout.write(
                        f'  CESE {dni} | {nombre[:40]} | '
                        f'{fecha_cese} | {motivo}'
                    )
                    if not self.dry:
                        try:
                            with transaction.atomic():
                                p.fecha_cese = fecha_cese
                                p.estado = 'Cesado'
                                p.motivo_cese = motivo[:20]
                                p.save(update_fields=['fecha_cese', 'estado', 'motivo_cese'])
                            ceses += 1
                        except Exception as e:
                            errores.append(f'CESE {dni}: {e}')
                    else:
                        ceses += 1
                continue  # nunca tocar condicion de existentes

            # ── Nuevo ──────────────────────────────────────────────────
            if not activo:
                self.stdout.write(
                    self.style.WARNING(
                        f'  SKIP cesado sin registro: {dni} | {nombre[:40]}'
                    )
                )
                continue

            area_nombre = _norm_key(row.get('Area', '') or '')
            subarea = subarea_map.get(area_nombre)
            if not subarea:
                for key, sa in subarea_map.items():
                    if area_nombre in key or key in area_nombre:
                        subarea = sa
                        break

            condicion = _norm_condicion(row.get('Condicion', 'LOCAL'))
            if condicion not in ('LOCAL', 'FORANEO', 'LIMA'):
                condicion = 'LOCAL'

            grupo_tareo = 'RCO' if condicion == 'FORANEO' else 'STAFF'
            fecha_ingreso = _parse_fecha(row.get('FechaIngreso'))
            tipo_doc = _norm_key(row.get('TipoDoc', 'DNI') or 'DNI')
            if tipo_doc not in ('DNI', 'CE', 'PASAPORTE', 'PTP'):
                tipo_doc = 'DNI'
            cargo = str(row.get('Cargo', '') or '').strip()[:150]
            celular = str(row.get('Celular', '') or '').strip()[:20]
            genero_raw = _norm_key(row.get('Genero', '') or '')
            sexo = 'M' if 'MASC' in genero_raw else ('F' if 'FEM' in genero_raw else '')
            fecha_nac = _parse_fecha(row.get('FechaNac'))

            self.stdout.write(
                f'  NUEVO {dni} | {nombre[:40]} | {cargo[:25]} | '
                f'{area_nombre} | {condicion} | {grupo_tareo} | '
                f'ing={fecha_ingreso}'
            )

            if not self.dry:
                try:
                    with transaction.atomic():
                        Personal.objects.create(
                            tipo_doc=tipo_doc,
                            nro_doc=dni,
                            apellidos_nombres=nombre[:250],
                            cargo=cargo,
                            tipo_trab='Empleado',
                            categoria='',
                            regimen_pension='AFP',
                            asignacion_familiar=False,
                            subarea=subarea,
                            fecha_alta=fecha_ingreso,
                            fecha_nacimiento=fecha_nac,
                            estado='Activo',
                            sexo=sexo,
                            celular=celular,
                            condicion=condicion,
                            grupo_tareo=grupo_tareo,
                            jornada_horas=Decimal('8.5'),
                            personal_clave=False,
                            renovacion_automatica=False,
                            dias_libres_corte_2025=Decimal('0'),
                            tiene_eps=False,
                            eps_descuento_mensual=Decimal('0'),
                            viaticos_mensual=Decimal('0'),
                            cond_trabajo_mensual=Decimal('0'),
                            alimentacion_mensual=Decimal('0'),
                        )
                    nuevos += 1
                    dnis_bd[dni] = Personal.objects.get(nro_doc=dni)
                except Exception as e:
                    msg = f'NUEVO {dni} ({nombre[:30]}): {e}'
                    errores.append(msg)
                    self.stdout.write(self.style.ERROR(f'    ERROR: {msg}'))
            else:
                nuevos += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n  Resumen personal:\n'
            f'    Nuevos creados:    {nuevos}\n'
            f'    Ceses aplicados:   {ceses}\n'
            f'    Ya cesados (skip): {skip_ya_cese}\n'
            f'    Errores:           {len(errores)}'
        ))
        for e in errores:
            self.stdout.write(self.style.ERROR(f'    ! {e}'))

    # ══════════════════════════════════════════════════════════════════════
    # 2. ASISTENCIA
    # ══════════════════════════════════════════════════════════════════════

    def _sync_asistencia(self):
        from personal.models import Personal
        from asistencia.models import RegistroTareo, TareoImportacion, FeriadoCalendario

        self.stdout.write('\n== [2/3] IMPORTACION DE ASISTENCIA ABRIL 2026 ==')

        pd = self.pd
        df = pd.read_excel(ARCHIVO_ASISTENCIA, sheet_name='Sheet',
                           dtype={'DNI': str}, engine='openpyxl')

        df['_dni']      = df['DNI'].apply(_norm_dni)
        df['_fecha']    = df['Fecha'].apply(_parse_fecha)
        df['_ingreso']  = df['Ingreso'].apply(_parse_hora_str)
        df['_salida']   = df['Salida'].apply(_parse_hora_str)
        df['_refrig']   = df.get('Refrigerio', pd.Series(dtype=str)).apply(_parse_hora_str)
        df['_fin_ref']  = df.get('FinRefrigerio', pd.Series(dtype=str)).apply(_parse_hora_str)

        df = df[df['_fecha'].notna() & (df['_dni'] != '')]

        personal_map: dict[str, Personal] = {p.nro_doc: p for p in Personal.objects.all()}

        fechas_validas = [f for f in df['_fecha'].unique() if f is not None]
        if not fechas_validas:
            self.stdout.write(self.style.ERROR('  Sin fechas válidas en el archivo.'))
            return

        fecha_min = min(fechas_validas)
        fecha_max = max(fechas_validas)

        feriados: set[date] = set(
            FeriadoCalendario.objects
            .filter(fecha__gte=fecha_min, fecha__lte=fecha_max, activo=True)
            .values_list('fecha', flat=True)
        )
        self.stdout.write(
            f'  Periodo: {fecha_min} a {fecha_max} | '
            f'Feriados en BD: {sorted(feriados) or "ninguno"}'
        )
        if not feriados:
            self.stdout.write(
                self.style.WARNING(
                    '  AVISO: no hay feriados cargados para abril. '
                    'Si Jueves/Viernes Santo deben procesarse como feriado, '
                    'cargarlos primero en Parametros > Feriados.'
                )
            )

        if not self.dry:
            importacion = TareoImportacion.objects.create(
                tipo='RELOJ',
                periodo_inicio=fecha_min,
                periodo_fin=fecha_max,
                estado='PROCESANDO',
                archivo_nombre='Asistencia_Detalle_Consorcio.xlsx',
                total_registros=len(df),
                errores=[],
                advertencias=[],
                metadata={'fuente': 'sync_datos_abril_2026'},
            )
            self.stdout.write(f'  TareoImportacion #{importacion.pk} creada')
        else:
            importacion = type('FakeImp', (), {'pk': 0})()

        creados = 0
        actualizados = 0
        sin_personal: list[str] = []
        errores: list[str] = []

        for _, row in df.iterrows():
            dni = row['_dni']
            fecha = row['_fecha']
            if fecha is None:
                continue

            personal = personal_map.get(dni)
            if not personal:
                if dni not in sin_personal:
                    sin_personal.append(dni)
                continue

            ingreso_s  = row['_ingreso']
            salida_s   = row['_salida']
            refrig_s   = row['_refrig']
            fin_ref_s  = row['_fin_ref']

            condicion = _norm_condicion(personal.condicion or 'LOCAL')
            if condicion not in JORNADA:
                condicion = 'LOCAL'
            dia_semana = fecha.weekday()
            jornada = JORNADA[condicion][dia_semana]
            es_feriado = fecha in feriados
            es_dom_local = dia_semana == 6 and condicion in ('LOCAL', 'LIMA')

            horas_marcadas = _calc_horas(ingreso_s, salida_s, refrig_s, fin_ref_s)

            if horas_marcadas is None:
                # Solo ingreso sin salida → SS
                codigo = 'SS'
                horas_marc_d = Decimal(str(jornada)) if jornada > 0 else Decimal('8.5')
                h_ef = float(horas_marc_d)
                h_norm = h_ef
                he25 = he35 = he100 = 0.0
            elif jornada > 0 and horas_marcadas < jornada / 2:
                # Marcación incompleta → SS implícito
                codigo = 'SS'
                horas_marc_d = Decimal(str(jornada))
                h_ef = float(horas_marc_d)
                h_norm = h_ef
                he25 = he35 = he100 = 0.0
            else:
                codigo = 'T'
                horas_marc_d = Decimal(str(horas_marcadas))
                # Auto-descuento almuerzo si no hay refrigerio y > 7h
                horas_ef = horas_marcadas
                if not refrig_s and horas_marcadas > 7.0:
                    horas_ef = horas_marcadas - 1.0
                h_ef, h_norm, he25, he35, he100 = _calc_he(
                    horas_ef, jornada, es_feriado, es_dom_local
                )

            grupo = personal.grupo_tareo or 'RCO'
            he_al_banco = grupo == 'STAFF'

            if not self.dry:
                try:
                    obj, created = RegistroTareo.objects.update_or_create(
                        importacion=importacion,
                        dni=dni,
                        fecha=fecha,
                        defaults=dict(
                            personal=personal,
                            codigo_dia=codigo,
                            fuente_codigo='RELOJ',
                            grupo=grupo,
                            condicion=condicion,
                            dia_semana=dia_semana,
                            es_feriado=es_feriado,
                            hora_entrada_real=_hora_str_a_time(ingreso_s),
                            hora_salida_real=_hora_str_a_time(salida_s),
                            horas_marcadas=horas_marc_d,
                            horas_efectivas=Decimal(str(round(h_ef, 2))),
                            horas_normales=Decimal(str(h_norm)),
                            he_25=Decimal(str(he25)),
                            he_35=Decimal(str(he35)),
                            he_100=Decimal(str(he100)),
                            he_al_banco=he_al_banco,
                            almuerzo_manual=Decimal('0'),  # 0 = auto calculado
                        ),
                    )
                    if created:
                        creados += 1
                    else:
                        actualizados += 1
                except Exception as e:
                    errores.append(f'{dni} {fecha}: {e}')
            else:
                creados += 1

        if not self.dry:
            importacion.estado = 'COMPLETADO' if not errores else 'COMPLETADO_CON_ERRORES'
            importacion.registros_ok = creados
            importacion.registros_error = len(errores)
            importacion.registros_sin_match = len(sin_personal)
            importacion.errores = errores[:50]
            importacion.save()

            if creados + actualizados > 0:
                self.stdout.write('  Actualizando BancoHoras STAFF...')
                self._actualizar_banco(personal_map, fecha_min, fecha_max)

        self.stdout.write(self.style.SUCCESS(
            f'\n  Resumen asistencia:\n'
            f'    Registros creados:      {creados}\n'
            f'    Registros actualizados: {actualizados}\n'
            f'    DNIs sin match BD:      {len(sin_personal)}\n'
            f'    Errores:                {len(errores)}'
        ))
        if sin_personal:
            self.stdout.write(f'    Sin match: {sin_personal[:15]}')
        for e in errores[:20]:
            self.stdout.write(self.style.ERROR(f'    ! {e}'))

    def _actualizar_banco(self, personal_map, fecha_min, fecha_max):
        from asistencia.models import BancoHoras, RegistroTareo
        from django.db.models import Sum

        staff = {dni: p for dni, p in personal_map.items() if p.grupo_tareo == 'STAFF'}
        periodos = set()
        periodos.add((fecha_min.year, fecha_min.month))
        periodos.add((fecha_max.year, fecha_max.month))

        for dni, personal in staff.items():
            for anio, mes in periodos:
                ci = date(anio - 1 if mes == 1 else anio,
                          12 if mes == 1 else mes - 1, 21)
                cf = date(anio, mes, 20)
                agg = RegistroTareo.objects.filter(
                    personal=personal, fecha__gte=ci, fecha__lte=cf,
                ).aggregate(
                    he25=Sum('he_25'), he35=Sum('he_35'), he100=Sum('he_100')
                )
                total_he = (agg['he25'] or Decimal('0')) + \
                           (agg['he35'] or Decimal('0')) + \
                           (agg['he100'] or Decimal('0'))
                if total_he == 0:
                    continue
                banco, _ = BancoHoras.objects.get_or_create(
                    personal=personal, periodo_anio=anio, periodo_mes=mes,
                    defaults={'cerrado': False},
                )
                if banco.cerrado:
                    continue
                banco.he_25_acumuladas  = agg['he25']  or Decimal('0')
                banco.he_35_acumuladas  = agg['he35']  or Decimal('0')
                banco.he_100_acumuladas = agg['he100'] or Decimal('0')
                banco.saldo_horas = (
                    banco.he_25_acumuladas + banco.he_35_acumuladas +
                    banco.he_100_acumuladas - banco.he_compensadas
                )
                banco.save()

    # ══════════════════════════════════════════════════════════════════════
    # 3. PAPELETAS
    # ══════════════════════════════════════════════════════════════════════

    def _sync_papeletas(self):
        from personal.models import Personal
        from asistencia.models import RegistroPapeleta

        self.stdout.write('\n== [3/3] IMPORTACION DE PAPELETAS ==')

        pd = self.pd
        df = pd.read_excel(ARCHIVO_PAPELETAS, sheet_name='Sheet',
                           dtype={'DNI': str}, engine='openpyxl')

        df['_dni']      = df['DNI'].apply(_norm_dni)
        df['_fecha_ini'] = df['FechaInicio'].apply(_parse_fecha)
        df['_fecha_fin'] = df['FechaFin'].apply(_parse_fecha)
        df = df[df['_fecha_ini'].notna() & df['_fecha_fin'].notna() & (df['_dni'] != '')]

        personal_map: dict[str, Personal] = {p.nro_doc: p for p in Personal.objects.all()}

        creadas = 0
        duplicadas = 0
        sin_personal: list[str] = []
        tipos_no_mapeados: list[str] = []
        errores: list[str] = []

        for _, row in df.iterrows():
            dni = row['_dni']
            fecha_ini = row['_fecha_ini']
            fecha_fin = row['_fecha_fin']
            if fecha_ini is None or fecha_fin is None:
                continue

            personal = personal_map.get(dni)
            if not personal:
                if dni not in sin_personal:
                    sin_personal.append(dni)
                continue

            tipo_raw = str(row.get('TipoPermiso', '') or '').strip()
            tipo_key = _norm_key(tipo_raw)
            tipo_permiso = TIPO_PERMISO_MAP.get(tipo_key)
            if not tipo_permiso:
                if tipo_raw not in tipos_no_mapeados:
                    tipos_no_mapeados.append(tipo_raw)
                tipo_permiso = 'OTRO'

            iniciales_raw = str(row.get('Iniciales', '') or '').strip().upper()[:10]
            detalle = str(row.get('Detalle', '') or '').strip()[:500]
            cargo = str(row.get('Cargo', '') or '').strip()[:150]
            area = str(row.get('Area Trabajo', '') or '').strip()[:150]

            dias_habiles = sum(
                1 for i in range((fecha_fin - fecha_ini).days + 1)
                if (fecha_ini + timedelta(days=i)).weekday() < 6
            )

            self.stdout.write(
                f'  {dni} | {personal.apellidos_nombres[:30]} | '
                f'{tipo_permiso} | {iniciales_raw} | {fecha_ini}>{fecha_fin} | {dias_habiles}d'
            )

            if not self.dry:
                try:
                    existe = RegistroPapeleta.objects.filter(
                        personal=personal,
                        tipo_permiso=tipo_permiso,
                        fecha_inicio=fecha_ini,
                        fecha_fin=fecha_fin,
                    ).exists()
                    if existe:
                        duplicadas += 1
                        self.stdout.write('    (duplicada, skip)')
                        continue

                    with transaction.atomic():
                        RegistroPapeleta.objects.create(
                            personal=personal,
                            dni=dni,
                            tipo_permiso=tipo_permiso,
                            tipo_permiso_raw=tipo_raw[:100],
                            iniciales=iniciales_raw,
                            fecha_inicio=fecha_ini,
                            fecha_fin=fecha_fin,
                            dias_habiles=dias_habiles,
                            detalle=detalle,
                            cargo=cargo,
                            area_trabajo=area,
                            estado='APROBADA',
                            origen='IMPORTACION',
                            nombre_archivo='PermisosLicencias_Personal.xlsx',
                        )
                    creadas += 1
                except Exception as e:
                    msg = f'{dni} {tipo_permiso} {fecha_ini}: {e}'
                    errores.append(msg)
                    self.stdout.write(self.style.ERROR(f'    ERROR: {msg}'))
            else:
                creadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n  Resumen papeletas:\n'
            f'    Papeletas creadas:    {creadas}\n'
            f'    Duplicadas (skip):    {duplicadas}\n'
            f'    DNIs sin match BD:    {len(sin_personal)}\n'
            f'    Tipos no mapeados:    {tipos_no_mapeados}\n'
            f'    Errores:              {len(errores)}'
        ))
        if sin_personal:
            self.stdout.write(f'    Sin match: {sin_personal}')
        for e in errores[:20]:
            self.stdout.write(self.style.ERROR(f'    ! {e}'))
