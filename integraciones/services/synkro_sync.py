"""
Sincronización directa con la BD remota de Synkro RRHH (SQL Server).

Lee desde la connection 'synkro' (read-only) las tablas:
  - PER_Personas + P_Personal  (maestro, match por DNI)
  - PicadosPersonal            (marcaciones biométricas)
  - PermisosLicencias          (papeletas)
  - Feriados                   (feriados nacionales)

Y escribe en la connection 'default' (Postgres Harmoni):
  - FeriadoCalendario          (upsert por fecha)
  - RegistroPapeleta           (upsert por id externo)
  - RegistroTareo              (upsert por personal+fecha; agrupa picados)

Diseño:
  - Incremental por defecto (lee desde el cursor de la última sync).
  - Idempotente: corrida repetida no duplica.
  - Respeta períodos CERRADOS (no toca esos días).
  - No sobrescribe registros con fuente=MANUAL ni fuente=PAPELETA con ref.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from integraciones.models import SyncSynkroLog
from integraciones.synkro_models import (
    FeriadoSynkro, PermisoLicencia, PerPersona, PPersonal, PicadoPersonal,
)

logger = logging.getLogger('asistencia')

CERO = Decimal('0')

# Mapeo IdTipoPermiso (Synkro) → tipo_permiso de RegistroPapeleta (Harmoni)
TIPO_PERMISO_MAP: dict[int, str | None] = {
    1:  'DESCANSO_MEDICO',
    2:  'LICENCIA_CON_GOCE',
    3:  'LICENCIA_SIN_GOCE',
    4:  'VACACIONES',
    5:  'LICENCIA_PATERNIDAD',
    6:  'BAJADAS',
    7:  'TRABAJO_REMOTO',
    8:  'COMISION_TRABAJO',
    9:  'SUSPENSION_ACTO_INSEGURO',
    10: 'LICENCIA_FALLECIMIENTO',
    11: 'OTRO',                    # ATM (atención médica) — no hay equivalente directo
    12: 'COMP_DIA_TRABAJO',
    13: 'SUSPENSION',              # AS (Amonestación)
    14: 'BAJADAS_ACUMULADAS',
    15: None,                      # FR (Feriado no recuperable) — se ignora
    16: 'COMPENSACION_HE',
    17: 'COMPENSACION_FERIADO',
}

# Fuentes de RegistroTareo que el sync puede sobrescribir con datos de reloj.
# MANUAL y PAPELETA se respetan siempre (gana edición manual / papeleta vigente).
FUENTES_REESCRIBIBLES = {
    'FALTA_AUTO', 'DESCANSO_SEMANAL', 'AUTO_LIMA', 'REGLA_ESPECIAL',
    'FERIADO', 'EXCEL', 'RELOJ',
}


def _normalizar_dni(dni: str | None) -> str:
    """Strip + collapse interno. No hace lpad ni cambia ceros — Harmoni
    guarda los DNIs como vienen, incluido el de extranjeros (con prefijo
    '00').
    """
    if not dni:
        return ''
    return str(dni).strip()


def _build_personal_index_por_dni() -> dict[str, int]:
    """{dni → personal_id} para match rápido en bucle."""
    from personal.models import Personal
    return {
        _normalizar_dni(p.nro_doc): p.id
        for p in Personal.objects.exclude(nro_doc__isnull=True).exclude(nro_doc='')
    }


def _build_synkro_personal_to_dni() -> dict[int, str]:
    """{P_Personal.IdPersonal (Synkro) → DNI}."""
    # JOIN P_Personal × PER_Personas vía IdPersona
    qs = PPersonal.objects.using('synkro').values_list('id_personal', 'id_persona')
    persona_map = dict(qs)  # personal_id → persona_id
    persona_ids = list(persona_map.values())
    dni_map = dict(
        PerPersona.objects.using('synkro')
        .filter(id_persona__in=persona_ids)
        .values_list('id_persona', 'dni')
    )
    return {pid: _normalizar_dni(dni_map.get(pers_id, ''))
            for pid, pers_id in persona_map.items()}


# ─────────────────────────────────────────────────────────────────────────
# SYNC FERIADOS
# ─────────────────────────────────────────────────────────────────────────


def sync_feriados() -> int:
    """Upsert FeriadoCalendario desde Synkro.Feriados. Retorna nuevos creados."""
    from asistencia.models import FeriadoCalendario
    creados = 0
    feriados_synkro = list(FeriadoSynkro.objects.using('synkro').all())
    fechas_existentes = set(
        FeriadoCalendario.objects.values_list('fecha', flat=True)
    )
    nuevos = []
    for f in feriados_synkro:
        if f.fecha in fechas_existentes:
            continue
        nuevos.append(FeriadoCalendario(
            fecha=f.fecha,
            nombre=(f.descripcion or 'Feriado').strip()[:150],
            activo=True,
        ))
    if nuevos:
        FeriadoCalendario.objects.bulk_create(nuevos, ignore_conflicts=True)
        creados = len(nuevos)
    return creados


# ─────────────────────────────────────────────────────────────────────────
# SYNC PAPELETAS
# ─────────────────────────────────────────────────────────────────────────


def sync_papeletas(cursor_desde: datetime | None,
                   personal_dni_map: dict[int, str],
                   personal_idx: dict[str, int]) -> dict:
    """Lee papeletas nuevas/modificadas desde Synkro y upsert en RegistroPapeleta.

    Match: la papeleta se identifica externamente por
    `(origen='SYNKRO', importacion=None, observaciones LIKE 'SYNKRO#{IdPermiso}')`
    para detectar duplicados en re-corridas.

    Retorna: {creadas, actualizadas, omitidas, no_encontradas, max_cursor}
    """
    from asistencia.models import RegistroPapeleta

    qs = PermisoLicencia.objects.using('synkro').all()
    if cursor_desde:
        # Tomar registros con FechaRegistro o FechaModifica >= cursor
        from django.db.models import Q
        qs = qs.filter(
            Q(fecha_registro__gte=cursor_desde) |
            Q(fecha_modifica__gte=cursor_desde)
        )
    qs = qs.order_by('id_permiso')

    creadas = actualizadas = omitidas = no_encontradas = 0
    max_cursor: datetime | None = None

    # Index existente por marca SYNKRO#{id}
    existentes_por_extid = {}
    for pap in RegistroPapeleta.objects.filter(
        observaciones__contains='SYNKRO#'
    ).only('id', 'observaciones', 'estado', 'tipo_permiso',
           'fecha_inicio', 'fecha_fin', 'detalle'):
        # Extract SYNKRO#{n} del campo observaciones
        marker = pap.observaciones.split('SYNKRO#')[1].split()[0] if 'SYNKRO#' in pap.observaciones else ''
        if marker.isdigit():
            existentes_por_extid[int(marker)] = pap

    for permiso in qs.iterator(chunk_size=200):
        # Cursor: latest de fecha_registro/fecha_modifica (ambos tz-aware
        # cuando vienen de SQL Server con USE_TZ=True).
        ts_candidates = [t for t in (permiso.fecha_modifica, permiso.fecha_registro)
                         if t is not None]
        if ts_candidates:
            ts = max(ts_candidates)
            if max_cursor is None or ts > max_cursor:
                max_cursor = ts

        tipo = TIPO_PERMISO_MAP.get(permiso.id_tipo_permiso)
        if not tipo:
            omitidas += 1
            continue

        dni = personal_dni_map.get(permiso.id_personal)
        if not dni:
            no_encontradas += 1
            continue
        personal_id = personal_idx.get(dni)
        if not personal_id:
            no_encontradas += 1
            continue

        defaults = {
            'personal_id': personal_id,
            'dni': dni,
            'tipo_permiso': tipo,
            'fecha_inicio': permiso.fecha_inicio,
            'fecha_fin': permiso.fecha_fin,
            'detalle': (permiso.detalle or '')[:500],
            'dias_habiles': (permiso.fecha_fin - permiso.fecha_inicio).days + 1,
            'estado': 'APROBADA',
            'origen': 'IMPORTACION',
            'observaciones': f'SYNKRO#{permiso.id_permiso} | sync auto',
        }

        existente = existentes_por_extid.get(permiso.id_permiso)
        if existente:
            # Actualizar solo si cambió algo material (rango/tipo/estado base)
            cambios = []
            if existente.tipo_permiso != tipo:
                cambios.append('tipo_permiso')
                existente.tipo_permiso = tipo
            if existente.fecha_inicio != permiso.fecha_inicio:
                cambios.append('fecha_inicio')
                existente.fecha_inicio = permiso.fecha_inicio
            if existente.fecha_fin != permiso.fecha_fin:
                cambios.append('fecha_fin')
                existente.fecha_fin = permiso.fecha_fin
            nuevo_detalle = (permiso.detalle or '')[:500]
            if (existente.detalle or '') != nuevo_detalle:
                cambios.append('detalle')
                existente.detalle = nuevo_detalle
            if cambios:
                existente.dias_habiles = (existente.fecha_fin - existente.fecha_inicio).days + 1
                cambios.append('dias_habiles')
                existente.save(update_fields=cambios)
                actualizadas += 1
            else:
                omitidas += 1
        else:
            # Crear (signal aplicar_papeleta sincroniza RegistroTareo)
            RegistroPapeleta.objects.create(**defaults)
            creadas += 1

    return {
        'creadas': creadas,
        'actualizadas': actualizadas,
        'omitidas': omitidas,
        'no_encontradas': no_encontradas,
        'max_cursor': max_cursor,
    }


# ─────────────────────────────────────────────────────────────────────────
# SYNC PICADOS → REGISTRO TAREO
# ─────────────────────────────────────────────────────────────────────────


def sync_picados(cursor_desde: datetime | None,
                 personal_dni_map: dict[int, str],
                 personal_idx: dict[str, int],
                 ventana_dias_max: int = 60) -> dict:
    """Lee picados nuevos desde el cursor y los consolida en RegistroTareo
    como 1 fila por (personal, fecha) usando MIN/MAX de Fecha como
    entrada/salida.

    Solo procesa picados de los últimos `ventana_dias_max` días aunque el
    cursor sea más antiguo (evita reprocesar histórico masivo en caso de
    reset accidental del cursor).
    """
    from asistencia.models import (
        FeriadoCalendario, RegistroTareo, TareoImportacion,
    )
    from asistencia.views.calendario import _recalcular_horas
    from cierre.models import PeriodoCierre

    # Determinar ventana real
    fecha_min = (timezone.now() - timedelta(days=ventana_dias_max)).date()
    if cursor_desde:
        cursor_fecha = cursor_desde.date()
        if cursor_fecha < fecha_min:
            cursor_fecha = fecha_min
    else:
        cursor_fecha = fecha_min

    # Cursor: usamos FechaSinMS (date) para incremental por día
    qs = (PicadoPersonal.objects.using('synkro')
          .filter(fecha_sin_ms__gte=cursor_fecha)
          .order_by('id_personal', 'fecha'))

    # Agrupar picados en memoria por (personal_id_synkro, fecha)
    grupos: dict[tuple[int, date], list[datetime]] = {}
    max_cursor: datetime | None = None
    for p in qs.iterator(chunk_size=2000):
        key = (p.id_personal, p.fecha_sin_ms)
        grupos.setdefault(key, []).append(p.fecha)
        if max_cursor is None or p.fecha > max_cursor:
            max_cursor = p.fecha

    if not grupos:
        return {'creados': 0, 'actualizados': 0, 'no_encontrados': 0,
                'omitidos_cerrado': 0, 'max_cursor': max_cursor}

    # Caches
    feriados_set = set(
        FeriadoCalendario.objects.filter(activo=True)
        .values_list('fecha', flat=True)
    )
    cerrados = set(
        PeriodoCierre.objects.filter(estado='CERRADO')
        .values_list('anio', 'mes')
    )
    imp_synkro, _ = TareoImportacion.objects.get_or_create(
        tipo='RELOJ', archivo_nombre='synkro_sync_directo',
        defaults={
            'estado': 'COMPLETADO', 'total_registros': 0,
            'periodo_inicio': date(2025, 1, 1), 'periodo_fin': date(2030, 12, 31),
        },
    )

    from personal.models import Personal
    personal_obj_cache: dict[int, Personal] = {}

    creados = actualizados = no_encontrados = omitidos_cerrado = 0

    for (id_personal_syn, fecha), picados in grupos.items():
        if (fecha.year, fecha.month) in cerrados:
            omitidos_cerrado += 1
            continue
        dni = personal_dni_map.get(id_personal_syn)
        if not dni:
            no_encontrados += 1
            continue
        pid_harmoni = personal_idx.get(dni)
        if not pid_harmoni:
            no_encontrados += 1
            continue

        # Cargar Personal una vez por persona en esta corrida
        if pid_harmoni not in personal_obj_cache:
            try:
                personal_obj_cache[pid_harmoni] = Personal.objects.get(pk=pid_harmoni)
            except Personal.DoesNotExist:
                no_encontrados += 1
                continue
        p_obj = personal_obj_cache[pid_harmoni]

        if not picados:
            continue
        entrada = min(picados).time()
        salida = max(picados).time() if len(picados) >= 2 else None

        es_feriado = fecha in feriados_set
        condicion = (p_obj.condicion or 'LOCAL').upper()
        grupo = p_obj.grupo_tareo or ('STAFF' if condicion.replace('Á', 'A') != 'FORANEO' else 'RCO')

        # Buscar registro existente
        reg = RegistroTareo.objects.filter(personal_id=pid_harmoni, fecha=fecha).first()
        if reg is None:
            # Crear nuevo
            reg = RegistroTareo(
                importacion=imp_synkro,
                personal_id=pid_harmoni,
                dni=dni,
                nombre_archivo=p_obj.apellidos_nombres or '',
                grupo=grupo, condicion=condicion,
                fecha=fecha, dia_semana=fecha.weekday(),
                es_feriado=es_feriado,
                hora_entrada_real=entrada,
                hora_salida_real=salida,
                codigo_dia='A' if salida else 'SS',
                fuente_codigo='RELOJ',
                he_al_banco=(grupo == 'STAFF'),
            )
            _recalcular_horas(reg)
            reg.save()
            creados += 1
        else:
            # Solo sobrescribir si la fuente es reescribible (no MANUAL/PAPELETA)
            if reg.fuente_codigo == 'MANUAL':
                continue
            if reg.fuente_codigo == 'PAPELETA' and (reg.papeleta_ref or '').startswith('PAP#'):
                # Día cubierto por papeleta vigente: respetar
                continue
            if reg.fuente_codigo not in FUENTES_REESCRIBIBLES:
                continue
            cambios = False
            if reg.hora_entrada_real != entrada:
                reg.hora_entrada_real = entrada
                cambios = True
            if reg.hora_salida_real != salida:
                reg.hora_salida_real = salida
                cambios = True
            if cambios or reg.fuente_codigo != 'RELOJ':
                reg.fuente_codigo = 'RELOJ'
                if reg.codigo_dia in ('FA', 'F', 'DS', 'NA', 'FER'):
                    reg.codigo_dia = 'A' if salida else 'SS'
                _recalcular_horas(reg)
                reg.save()
                actualizados += 1

    return {
        'creados': creados,
        'actualizados': actualizados,
        'no_encontrados': no_encontrados,
        'omitidos_cerrado': omitidos_cerrado,
        'max_cursor': max_cursor,
    }


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTADOR
# ─────────────────────────────────────────────────────────────────────────


def _ultimo_cursor() -> tuple[datetime | None, datetime | None]:
    """(cursor_papeletas, cursor_picados) del último log OK."""
    last = (SyncSynkroLog.objects
            .filter(estado='OK')
            .order_by('-iniciado_en')
            .first())
    if not last:
        return None, None
    return last.cursor_papeletas, last.cursor_picados


def run_sync(usuario=None, origen: str = 'AUTO',
             ventana_picados_dias: int = 60) -> SyncSynkroLog:
    """Corre el sync completo. Crea SyncSynkroLog y lo retorna.

    Excepciones propagadas se capturan y se guardan en error_mensaje.
    """
    log = SyncSynkroLog.objects.create(
        origen=origen, usuario=usuario, estado='EN_PROGRESO',
    )
    t0 = time.time()
    try:
        cursor_pap_prev, cursor_pic_prev = _ultimo_cursor()

        # 1. Maestros y mapping de DNI
        personal_idx = _build_personal_index_por_dni()
        personal_dni_map = _build_synkro_personal_to_dni()

        # 2. Feriados (full upsert; no necesita cursor)
        feriados_creados = sync_feriados()

        # 3. Papeletas (incremental)
        with transaction.atomic():
            res_pap = sync_papeletas(cursor_pap_prev, personal_dni_map, personal_idx)

        # 4. Picados (incremental)
        res_pic = sync_picados(cursor_pic_prev, personal_dni_map, personal_idx,
                               ventana_dias_max=ventana_picados_dias)

        log.feriados_creados = feriados_creados
        log.papeletas_creadas = res_pap['creadas']
        log.papeletas_actualizadas = res_pap['actualizadas']
        log.papeletas_omitidas = res_pap['omitidas']
        log.registros_tareo_creados = res_pic['creados']
        log.registros_tareo_actualizados = res_pic['actualizados']
        log.personas_no_encontradas = (
            res_pap['no_encontradas'] + res_pic['no_encontrados']
        )
        log.cursor_papeletas = res_pap['max_cursor'] or cursor_pap_prev
        log.cursor_picados = res_pic['max_cursor'] or cursor_pic_prev
        log.estado = 'OK'
        log.detalle = {
            'papeletas': res_pap | {'max_cursor': str(res_pap.get('max_cursor') or '')},
            'picados': {**res_pic, 'max_cursor': str(res_pic.get('max_cursor') or '')},
            'feriados': {'creados': feriados_creados},
            'personal_synkro_total': len(personal_dni_map),
            'personal_harmoni_total': len(personal_idx),
        }
    except Exception as exc:
        logger.exception('Sync Synkro falló')
        log.estado = 'ERROR'
        log.error_mensaje = f'{type(exc).__name__}: {exc}'[:2000]
    finally:
        log.finalizado_en = timezone.now()
        log.duracion_segundos = round(time.time() - t0, 2)
        log.save()
    return log
