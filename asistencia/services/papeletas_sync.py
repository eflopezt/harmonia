"""
Sincronización automática Papeleta ↔ RegistroTareo.

Funciones reutilizables invocadas desde:
  - Signals (post_save / post_delete de RegistroPapeleta)
  - Comando de management sync_papeletas_registros (reconciliación masiva)

Reglas:
  - Papeleta en estado APROBADA/EJECUTADA → sus días cubren RegistroTareo con
    el código derivado de tipo_permiso (ef=HE=0).
  - Papeleta en RECHAZADA/ANULADA/PENDIENTE o eliminada → días se restauran
    al código "default" (FA, DS, FER según reglas de calendario).
  - Nunca sobrescribe días con RELOJ+ef>0 ni fuente MANUAL (trabajo real gana).
"""
from datetime import date, timedelta
from decimal import Decimal

from asistencia.models import (
    FeriadoCalendario, RegistroPapeleta, RegistroTareo, TareoImportacion,
)


CERO = Decimal('0')

# Códigos auto que el sync puede sobrescribir.
CODIGOS_AUTO = {'FA', 'DS', 'NA', 'CPF', 'FER', 'DL', 'DLA', 'CHE', 'VAC',
                'DM', 'LCG', 'LSG', 'LF', 'LP', 'LM', 'CT', 'CDT', 'SUS',
                'SAI', 'CAP', 'TR', 'OTR'}

TIPO_A_CODIGO = {
    'BAJADAS':                  'DL',
    'BAJADAS_ACUMULADAS':       'DLA',
    'VACACIONES':               'VAC',
    'DESCANSO_MEDICO':          'DM',
    'COMPENSACION_HE':          'CHE',
    'LICENCIA_CON_GOCE':        'LCG',
    'LICENCIA_SIN_GOCE':        'LSG',
    'LICENCIA_FALLECIMIENTO':   'LF',
    'LICENCIA_PATERNIDAD':      'LP',
    'LICENCIA_MATERNIDAD':      'LM',
    'COMISION_TRABAJO':         'CT',
    'COMPENSACION_FERIADO':     'CPF',
    'COMP_DIA_TRABAJO':         'CDT',
    'SUSPENSION':               'SUS',
    'SUSPENSION_ACTO_INSEGURO': 'SAI',
    'CAPACITACION':             'CAP',
    'TRABAJO_REMOTO':           'CT',
    'OTRO':                     'OTR',
}


def _cond_norm(c: str) -> str:
    return (c or 'LOCAL').upper().replace('Á', 'A').replace('Ñ', 'N')


def _codigo_default(personal, fecha: date, es_feriado: bool) -> tuple[str, str]:
    """Retorna (codigo, fuente) para un día sin papeleta ni marcación real."""
    cond = _cond_norm(personal.condicion)
    dow = fecha.weekday()
    if es_feriado:
        return 'FER', 'FERIADO'
    if dow == 6 and cond in ('LOCAL', 'LIMA'):
        return 'DS', 'DESCANSO_SEMANAL'
    if cond == 'LIMA' and dow < 6:
        return 'A', 'AUTO_LIMA'
    return 'FA', 'FALTA_AUTO'


def _es_trabajo_real(r: RegistroTareo) -> bool:
    """Día marcado por biométrico / ingreso manual: no sobrescribir."""
    if r.fuente_codigo == 'MANUAL':
        return True
    if r.fuente_codigo == 'RELOJ' and (r.horas_efectivas or CERO) > CERO:
        return True
    return False


def aplicar_papeleta(pap: RegistroPapeleta) -> dict:
    """Aplica el código derivado de la papeleta a todos los días cubiertos.

    Solo sobrescribe registros auto o inexistentes. Retorna stats.
    """
    stats = {'actualizados': 0, 'creados': 0, 'skip_trabajo_real': 0,
             'skip_sin_mapeo': 0, 'skip_sin_personal': 0}
    if pap.personal_id is None:
        stats['skip_sin_personal'] = 1
        return stats
    codigo = TIPO_A_CODIGO.get(pap.tipo_permiso)
    if not codigo:
        stats['skip_sin_mapeo'] = 1
        return stats

    imp = _get_or_create_imp()
    feriados = _feriados_cache(pap.fecha_inicio, pap.fecha_fin)

    a_crear = []
    d = pap.fecha_inicio
    while d <= pap.fecha_fin:
        es_feriado = d in feriados
        r = RegistroTareo.objects.filter(personal=pap.personal, fecha=d).first()
        if r is None:
            cond = pap.personal.condicion or 'LOCAL'
            grupo = pap.personal.grupo_tareo or ('STAFF' if _cond_norm(cond) != 'FORANEO' else 'RCO')
            a_crear.append(RegistroTareo(
                importacion=imp,
                personal=pap.personal,
                dni=pap.personal.nro_doc,
                nombre_archivo=pap.personal.apellidos_nombres,
                grupo=grupo, condicion=cond,
                fecha=d, dia_semana=d.weekday(),
                es_feriado=es_feriado,
                codigo_dia=codigo,
                fuente_codigo='PAPELETA',
                horas_efectivas=CERO, horas_normales=CERO,
                he_25=CERO, he_35=CERO, he_100=CERO,
                he_al_banco=(grupo == 'STAFF'),
                papeleta_ref=f'PAP#{pap.pk}',
            ))
            stats['creados'] += 1
        elif _es_trabajo_real(r):
            stats['skip_trabajo_real'] += 1
        elif r.codigo_dia != codigo:
            r.codigo_dia = codigo
            r.fuente_codigo = 'PAPELETA'
            r.horas_efectivas = CERO
            r.horas_normales = CERO
            r.he_25 = CERO
            r.he_35 = CERO
            r.he_100 = CERO
            r.papeleta_ref = f'PAP#{pap.pk}'
            r.save(update_fields=['codigo_dia', 'fuente_codigo',
                                   'horas_efectivas', 'horas_normales',
                                   'he_25', 'he_35', 'he_100', 'papeleta_ref'])
            stats['actualizados'] += 1
        d += timedelta(days=1)

    if a_crear:
        RegistroTareo.objects.bulk_create(a_crear, batch_size=200)
    return stats


def revertir_papeleta(pap: RegistroPapeleta) -> dict:
    """Restaura a código default los días que estaban con esta papeleta.

    Reconoce la papeleta por papeleta_ref=f'PAP#{pap.pk}'.
    Si hay otra papeleta aprobada en el mismo día, la respeta.
    """
    stats = {'restaurados': 0, 'skip_trabajo_real': 0,
             'replazados_otra_pap': 0, 'skip_sin_personal': 0}
    if pap.personal_id is None:
        stats['skip_sin_personal'] = 1
        return stats
    feriados = _feriados_cache(pap.fecha_inicio, pap.fecha_fin)

    ref = f'PAP#{pap.pk}'
    regs = RegistroTareo.objects.filter(
        personal=pap.personal,
        fecha__gte=pap.fecha_inicio, fecha__lte=pap.fecha_fin,
        papeleta_ref=ref,
    )
    for r in regs:
        if _es_trabajo_real(r):
            stats['skip_trabajo_real'] += 1
            continue
        # ¿Hay otra papeleta aprobada cubriendo ese día?
        otra = RegistroPapeleta.objects.filter(
            personal=pap.personal,
            estado__in=['APROBADA', 'EJECUTADA'],
            fecha_inicio__lte=r.fecha,
            fecha_fin__gte=r.fecha,
        ).exclude(pk=pap.pk).order_by('-id').first()
        if otra:
            codigo_nueva = TIPO_A_CODIGO.get(otra.tipo_permiso, 'FA')
            r.codigo_dia = codigo_nueva
            r.fuente_codigo = 'PAPELETA'
            r.papeleta_ref = f'PAP#{otra.pk}'
            stats['replazados_otra_pap'] += 1
        else:
            codigo, fuente = _codigo_default(pap.personal, r.fecha, r.fecha in feriados)
            r.codigo_dia = codigo
            r.fuente_codigo = fuente
            r.papeleta_ref = ''
            stats['restaurados'] += 1
        r.horas_efectivas = CERO
        r.horas_normales = CERO
        r.he_25 = CERO
        r.he_35 = CERO
        r.he_100 = CERO
        r.save(update_fields=['codigo_dia', 'fuente_codigo', 'papeleta_ref',
                               'horas_efectivas', 'horas_normales',
                               'he_25', 'he_35', 'he_100'])
    return stats


# ── helpers de caché ───────────────────────────────────────────────
_imp_cache = {'imp': None}
def _get_or_create_imp() -> TareoImportacion:
    if _imp_cache['imp'] is None or _imp_cache['imp'].pk is None:
        _imp_cache['imp'] = TareoImportacion.objects.create(
            archivo_nombre='papeletas_sync_auto',
            tipo='RELOJ',
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=date(2030, 12, 31),
            estado='COMPLETADO',
        )
    return _imp_cache['imp']


_feriados_cache_data = {'set': None, 'year_range': None}
def _feriados_cache(ini: date, fin: date) -> set:
    key = (ini.year, fin.year)
    if _feriados_cache_data['year_range'] != key:
        _feriados_cache_data['set'] = set(
            FeriadoCalendario.objects.filter(
                fecha__year__gte=ini.year, fecha__year__lte=fin.year, activo=True
            ).values_list('fecha', flat=True)
        )
        _feriados_cache_data['year_range'] = key
    return _feriados_cache_data['set']


def reset_caches():
    _imp_cache['imp'] = None
    _feriados_cache_data['year_range'] = None
    _feriados_cache_data['set'] = None
