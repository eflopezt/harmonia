"""
Repara las inconsistencias horas_efectivas ≠ horas_normales + HE25 + HE35 + HE100
detectadas en RegistroTareo.

Reglas aplicadas (confirmadas con el usuario):
  P1 — 01-ene-2026 (Año Nuevo): marcar `es_feriado=True` y aplicar regla
       feriado. Si hubo marcación → todo a he_100. Si no, día pagado.
  P2 — entrada == salida con marc=0 (sin salida real): tratar como SS
       → ef = norm = jornada del día, HE = 0.
  P3 — domingo 22-mar LOCAL con h100 = ef - 1h: LOCAL domingo todo al 100%
       → norm = 0, h100 = ef, HE25 = HE35 = 0.
  P4 — norm > ef (trabajó menos que jornada / no marcó salida):
       el usuario pide que se considere SS → ef = norm = jornada del día,
       HE = 0.

Caso general (fallback): aplica la lógica del processor:
  - Si ef <= jornada → norm = ef, HE = 0
  - Si ef > jornada → norm = jornada, he_25 = min(exc, 2), he_35 = max(0, exc-2)

No toca `horas_marcadas` (valor bruto del reloj).
Todos los valores salen redondeados al múltiplo de 0.5.
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from asistencia.models import (
    ConfiguracionSistema, FeriadoCalendario, RegistroTareo,
)
from asistencia.services.processor import redondear_media_hora


CERO = Decimal('0')
DOS = Decimal('2')
JORNADA_SAB_LOCAL = Decimal('5.5')
JORNADA_DOM_FORANEO = Decimal('4')


def jornada_del_dia(condicion: str, fecha: date, config: ConfiguracionSistema) -> Decimal:
    """Retorna la jornada legal del día según condición + día de semana."""
    cond = (condicion or 'LOCAL').upper().replace('Á', 'A')
    ds = fecha.weekday()  # 0=Lun … 6=Dom
    if cond == 'FORANEO':
        if ds == 6:
            return JORNADA_DOM_FORANEO
        return Decimal(str(config.jornada_foraneo_horas))
    # LOCAL / LIMA
    if ds == 6:
        return CERO  # domingo LOCAL → todo HE100 si trabaja
    if ds == 5:
        return JORNADA_SAB_LOCAL
    return Decimal(str(config.jornada_local_horas))


def _es_inconsistente(r: RegistroTareo) -> bool:
    suma = Decimal(r.horas_normales or 0) + Decimal(r.he_25 or 0) + \
           Decimal(r.he_35 or 0) + Decimal(r.he_100 or 0)
    ef = Decimal(r.horas_efectivas or 0)
    return abs(ef - suma) > Decimal('0.01')


def _aplicar_dia_normal(r: RegistroTareo, ef: Decimal, jornada: Decimal):
    """Reparte horas efectivas en un día normal (no feriado, no descanso)."""
    if ef <= jornada:
        r.horas_normales = ef
        r.he_25 = r.he_35 = r.he_100 = CERO
    else:
        r.horas_normales = jornada
        exceso = ef - jornada
        r.he_25 = min(exceso, DOS)
        r.he_35 = max(CERO, exceso - DOS)
        r.he_100 = CERO


def _aplicar_feriado_o_dom_local(r: RegistroTareo, ef: Decimal,
                                 jornada: Decimal, cond_norm: str,
                                 es_feriado: bool, es_dom: bool):
    """Reparte ef en feriado / descanso semanal trabajado."""
    if es_feriado or (es_dom and cond_norm != 'FORANEO'):
        # Feriado (cualquier condición) o LOCAL/LIMA domingo → todo al 100%
        r.horas_normales = CERO
        r.he_25 = r.he_35 = CERO
        r.he_100 = ef
    else:
        # FORANEO domingo: normal hasta jornada (4h), exceso HE 100%
        r.horas_normales = min(ef, jornada)
        r.he_25 = r.he_35 = CERO
        r.he_100 = max(CERO, ef - jornada)


def _redondear_campos(r: RegistroTareo):
    r.horas_efectivas = redondear_media_hora(r.horas_efectivas)
    r.horas_normales = redondear_media_hora(r.horas_normales)
    r.he_25 = redondear_media_hora(r.he_25)
    r.he_35 = redondear_media_hora(r.he_35)
    r.he_100 = redondear_media_hora(r.he_100)


class Command(BaseCommand):
    help = 'Repara inconsistencias en horas_efectivas / normales / HE para RegistroTareo.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='No guarda cambios, solo muestra impacto.')
        parser.add_argument('--anio', type=int, default=2026,
                            help='Año a revisar (default 2026).')
        parser.add_argument('--limite-ejemplos', type=int, default=15)

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        anio = opts['anio']
        lim = opts['limite_ejemplos']

        config = ConfiguracionSistema.objects.first()
        if not config:
            self.stderr.write('ConfiguracionSistema no existe')
            return

        feriados = set(FeriadoCalendario.objects.values_list('fecha', flat=True))
        self.stdout.write(f'Feriados cargados: {len(feriados)}')

        qs = RegistroTareo.objects.filter(fecha__year=anio).select_related('personal')

        a_actualizar = []
        stats = {'P1': 0, 'P2': 0, 'P3': 0, 'P4': 0, 'P5': 0, 'skip': 0}
        ejemplos = []

        for r in qs.iterator(chunk_size=500):
            if not _es_inconsistente(r):
                continue

            personal = r.personal
            if not personal:
                stats['skip'] += 1
                continue

            condicion = (r.condicion or personal.condicion or 'LOCAL')
            cond_norm = condicion.upper().replace('Á', 'A')
            ds = r.dia_semana if r.dia_semana is not None else r.fecha.weekday()
            es_dom = ds == 6
            jornada = jornada_del_dia(condicion, r.fecha, config)

            # ── P1: 01-ene-2026 (Año Nuevo) mal marcado ────────────────
            if r.fecha == date(2026, 1, 1) and not r.es_feriado:
                r.es_feriado = True
                # fall through con es_feriado=True

            es_feriado = r.es_feriado or r.fecha in feriados

            antes = (r.horas_efectivas, r.horas_normales, r.he_25, r.he_35, r.he_100)
            patron = 'P5'

            # ── P2: entrada == salida con marc=0 → SS ──────────────────
            if (Decimal(r.horas_marcadas or 0) == 0
                    and r.hora_entrada_real and r.hora_salida_real
                    and r.hora_entrada_real == r.hora_salida_real
                    and (Decimal(r.he_25 or 0) > 0 or Decimal(r.he_35 or 0) > 0)):
                j = jornada if jornada > 0 else Decimal('8.5')
                r.horas_efectivas = j
                r.horas_normales = j
                r.he_25 = r.he_35 = r.he_100 = CERO
                r.codigo_dia = 'SS'
                patron = 'P2'

            # ── P3: domingo LOCAL 22-mar — h100 = ef - 1 ──────────────
            elif (es_dom and cond_norm != 'FORANEO'
                    and r.codigo_dia == 'DS'
                    and Decimal(r.horas_efectivas or 0) > 0):
                ef = Decimal(r.horas_efectivas)
                _aplicar_feriado_o_dom_local(r, ef, jornada, cond_norm, False, True)
                patron = 'P3'

            # ── P4: norm > ef — trabajó menos o no marcó salida → SS ─
            elif Decimal(r.horas_normales or 0) > Decimal(r.horas_efectivas or 0):
                j = jornada if jornada > 0 else Decimal('8.5')
                r.horas_efectivas = j
                r.horas_normales = j
                r.he_25 = r.he_35 = r.he_100 = CERO
                patron = 'P4'

            # ── P1: feriado 01-ene con valores mal ────────────────────
            elif r.fecha == date(2026, 1, 1):
                ef = Decimal(r.horas_efectivas or 0)
                if ef > 0:
                    # Feriado laborado: todo a 100%
                    _aplicar_feriado_o_dom_local(r, ef, jornada,
                                                 cond_norm, True, es_dom)
                else:
                    # Feriado no laborado: día pagado sin HE
                    j = jornada if jornada > 0 else Decimal('8.5')
                    r.horas_efectivas = j
                    r.horas_normales = j
                    r.he_25 = r.he_35 = r.he_100 = CERO
                patron = 'P1'

            # ── P5: fallback — recalcular desde ef con jornada del día
            else:
                ef = Decimal(r.horas_efectivas or 0)
                if es_feriado or es_dom:
                    _aplicar_feriado_o_dom_local(r, ef, jornada,
                                                 cond_norm, es_feriado, es_dom)
                else:
                    _aplicar_dia_normal(r, ef, jornada)

            _redondear_campos(r)
            stats[patron] += 1
            a_actualizar.append(r)

            if len(ejemplos) < lim:
                despues = (r.horas_efectivas, r.horas_normales,
                           r.he_25, r.he_35, r.he_100)
                ejemplos.append((patron, r.fecha, r.dni,
                                 r.codigo_dia, cond_norm, antes, despues))

        # ── Reporte ─────────────────────────────────────────────────
        self.stdout.write(f'\nTotal a corregir: {len(a_actualizar)}')
        self.stdout.write('Por patrón:')
        for k, v in stats.items():
            self.stdout.write(f'  {k}: {v}')

        self.stdout.write(f'\nEjemplos ({len(ejemplos)}):')
        for p, f, dni, cod, cnd, a, d in ejemplos:
            self.stdout.write(
                f'  [{p}] {f} {dni} cod={cod or "-":5s} cond={cnd:8s}'
            )
            self.stdout.write(
                f'      antes : ef={a[0]} norm={a[1]} h25={a[2]} h35={a[3]} h100={a[4]}'
            )
            self.stdout.write(
                f'      despues: ef={d[0]} norm={d[1]} h25={d[2]} h35={d[3]} h100={d[4]}'
            )

        if dry:
            self.stdout.write(self.style.WARNING('\nDRY RUN - no se guardó nada.'))
            return

        if not a_actualizar:
            return

        with transaction.atomic():
            RegistroTareo.objects.bulk_update(
                a_actualizar,
                ['horas_efectivas', 'horas_normales', 'he_25', 'he_35', 'he_100',
                 'es_feriado', 'codigo_dia'],
                batch_size=500,
            )
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Actualizados {len(a_actualizar)} registros.'
        ))
