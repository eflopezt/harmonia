"""
fix_domingos_feriados — Corrección masiva de horas en domingos y feriados.

PROBLEMA:
  Registros LOCAL/LIMA en domingos tenían horas_normales > 0 (lógica incorrecta).
  Feriados de cualquier condición también tenían horas_normales > 0.
  La regla correcta:
    · LOCAL/LIMA domingo    → TODAS las horas como he_100 (100%), horas_normales=0
    · Feriado (cualquier cond.) → TODAS las horas como he_100 (100%), horas_normales=0
    · FORÁNEO domingo       → hasta jornada_domingo_horas (4h) como normal,
                              exceso como he_100

USO:
  python manage.py fix_domingos_feriados
  python manage.py fix_domingos_feriados --dry-run
  python manage.py fix_domingos_feriados --fecha-ini 2026-01-01 --fecha-fin 2026-03-31
  python manage.py fix_domingos_feriados -v 2   # verbose: muestra cada fila
  python manage.py fix_domingos_feriados --solo-tareo   # sin recalcular BancoHoras
"""
import logging
from datetime import date
from decimal import Decimal
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum, Q

from asistencia.models import (
    RegistroTareo,
    TareoImportacion,
    BancoHoras,
    ConfiguracionSistema,
)

logger = logging.getLogger(__name__)

CERO = Decimal('0')
DOS  = Decimal('2')

JORNADA_SABADO_LOCAL = Decimal('5.5')

CODIGOS_SIN_HE = {
    'DL', 'DLA', 'CHE', 'VAC', 'DM', 'LCG', 'LF',
    'LP', 'LSG', 'FA', 'TR', 'CDT', 'CPF', 'FR', 'ATM', 'SAI',
}

DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def _cond_norm(condicion: str) -> str:
    return (condicion or '').upper().replace('Á', 'A').replace('À', 'A')


def _jornada_correcta(config, condicion: str, dia_semana: int) -> Decimal:
    cn = _cond_norm(condicion)
    if dia_semana == 6:                        # domingo
        if cn == 'FORANEO':
            return Decimal(str(config.jornada_domingo_horas))
        return CERO                            # LOCAL/LIMA: descanso → todo al 100%
    if cn == 'FORANEO':
        return Decimal(str(config.jornada_foraneo_horas))
    if dia_semana == 5:                        # sábado
        return JORNADA_SABADO_LOCAL
    return Decimal(str(config.jornada_local_horas))


def _recalcular_horas(codigo, horas_marcadas, jornada_h, es_feriado, dia_semana):
    """
    Replica processor._calcular_horas() con jornada correcta.
    Devuelve (horas_efectivas, horas_normales, he_25, he_35, he_100).
    """
    if codigo == 'SS':
        j = jornada_h if jornada_h > CERO else Decimal('8.5')
        # LOCAL domingo o feriado: SS también al 100%
        es_descanso = (dia_semana == 6)
        if (es_feriado or es_descanso) and (es_feriado or jornada_h == CERO):
            return j, CERO, CERO, CERO, j
        return j, j, CERO, CERO, CERO

    if codigo in CODIGOS_SIN_HE:
        return CERO, CERO, CERO, CERO, CERO

    if not horas_marcadas or horas_marcadas <= CERO:
        return jornada_h, jornada_h, CERO, CERO, CERO

    horas_m = Decimal(str(horas_marcadas))

    # Descuento almuerzo
    if jornada_h > Decimal('9'):
        horas_ef = horas_m
    elif jornada_h <= Decimal('6') or dia_semana == 5:
        horas_ef = horas_m
    else:
        almuerzo = Decimal('0.5') if horas_m > 5 else CERO
        horas_ef = max(CERO, horas_m - almuerzo)

    if horas_ef <= CERO:
        return CERO, CERO, CERO, CERO, CERO

    # Feriado o descanso semanal
    if es_feriado or dia_semana == 6:
        if es_feriado or jornada_h == CERO:
            # LOCAL domingo o cualquier feriado → TODAS al 100%
            return horas_ef, CERO, CERO, CERO, horas_ef
        else:
            # FORÁNEO domingo → normal hasta jornada + exceso HE 100%
            h_norm = min(horas_ef, jornada_h)
            he100  = max(CERO, horas_ef - jornada_h)
            return horas_ef, h_norm, CERO, CERO, he100

    # Día normal
    if horas_ef <= jornada_h:
        return horas_ef, horas_ef, CERO, CERO, CERO

    exceso = horas_ef - jornada_h
    he25   = min(exceso, DOS)
    he35   = max(CERO, exceso - DOS)
    return horas_ef, jornada_h, he25, he35, CERO


class Command(BaseCommand):
    help = (
        'Corrección masiva: domingos LOCAL/LIMA y feriados de cualquier condición. '
        'Asegura que horas_normales=0 y he_100=horas_efectivas en estos casos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Muestra cambios sin escribir.')
        parser.add_argument('--fecha-ini', default='2026-01-01', metavar='YYYY-MM-DD',
                            help='Inicio del rango (default: 2026-01-01).')
        parser.add_argument('--fecha-fin', default='2026-12-31', metavar='YYYY-MM-DD',
                            help='Fin del rango (default: 2026-12-31).')
        parser.add_argument('--solo-tareo', action='store_true',
                            help='Solo corrige RegistroTareo, sin recalcular BancoHoras.')
        parser.add_argument('--solo-banco', action='store_true',
                            help='Solo recalcula BancoHoras (asume tareo ya corregido).')

    def _sep(self, c='─', n=72):
        self.stdout.write(c * n)

    def _fix_registros(self, qs, config, dry_run, verbosity):
        actualizados = 0
        sin_cambio   = 0
        errores      = 0
        a_guardar    = []
        personal_set = set()

        for reg in qs.iterator(chunk_size=500):
            try:
                jornada_h = _jornada_correcta(config, reg.condicion, reg.dia_semana)

                h_ef, h_norm, he25, he35, he100 = _recalcular_horas(
                    codigo         = reg.codigo_dia or '',
                    horas_marcadas = reg.horas_marcadas,
                    jornada_h      = jornada_h,
                    es_feriado     = reg.es_feriado,
                    dia_semana     = reg.dia_semana,
                )

                changed = (
                    reg.horas_efectivas != h_ef  or
                    reg.horas_normales  != h_norm or
                    reg.he_25           != he25   or
                    reg.he_35           != he35   or
                    reg.he_100          != he100
                )

                if not changed:
                    sin_cambio += 1
                    continue

                if verbosity >= 2:
                    nombre = (
                        reg.personal.apellidos_nombres if reg.personal
                        else reg.nombre_archivo or reg.dni or '?'
                    )
                    ds  = DIAS[reg.dia_semana] if 0 <= reg.dia_semana <= 6 else '?'
                    fer = ' [FERIADO]' if reg.es_feriado else ''
                    cn  = _cond_norm(reg.condicion)
                    self.stdout.write(
                        f'  {reg.fecha} {ds:<3}{fer} | {cn:<7} | '
                        f'{reg.codigo_dia or "---":<5} | '
                        f'{nombre[:30]:<30} | '
                        f'n:{float(reg.horas_normales or 0):4.1f}→{float(h_norm):4.1f}  '
                        f'100%:{float(reg.he_100 or 0):4.1f}→{float(he100):4.1f}  '
                        f'ef:{float(reg.horas_efectivas or 0):4.1f}→{float(h_ef):4.1f}'
                    )

                if not dry_run:
                    reg.horas_efectivas = h_ef
                    reg.horas_normales  = h_norm
                    reg.he_25           = he25
                    reg.he_35           = he35
                    reg.he_100          = he100
                    a_guardar.append(reg)

                actualizados += 1
                if reg.personal_id:
                    personal_set.add(reg.personal_id)

            except Exception as exc:
                errores += 1
                self.stderr.write(self.style.ERROR(
                    f'  ERROR reg={reg.pk} ({reg.fecha} {reg.dni}): {exc}'))

        if not dry_run and a_guardar:
            with transaction.atomic():
                RegistroTareo.objects.bulk_update(
                    a_guardar,
                    ['horas_efectivas', 'horas_normales', 'he_25', 'he_35', 'he_100'],
                    batch_size=300,
                )

        return actualizados, sin_cambio, errores, personal_set

    def _fix_banco(self, fecha_ini, fecha_fin, dry_run, verbosity):
        """Recalcula BancoHoras para todas las importaciones que toquen el rango."""
        importaciones = (
            TareoImportacion.objects
            .filter(
                registros__fecha__gte=fecha_ini,
                registros__fecha__lte=fecha_fin,
                registros__grupo='STAFF',
            )
            .distinct()
            .order_by('periodo_fin')
        )

        if not importaciones.exists():
            self.stdout.write(self.style.WARNING(
                '  No se encontraron importaciones STAFF en el rango.'))
            return 0, 0

        b_act = 0
        b_new = 0

        for imp in importaciones:
            anio = imp.periodo_fin.year
            mes  = imp.periodo_fin.month

            if verbosity >= 1:
                self.stdout.write(
                    f'  Importación #{imp.pk} | {imp.periodo_inicio} → '
                    f'{imp.periodo_fin} → BancoHoras {anio}/{mes:02d}')

            resumen = (
                RegistroTareo.objects
                .filter(importacion=imp, grupo='STAFF', personal__isnull=False)
                .values('personal_id')
                .annotate(
                    s25=Sum('he_25'),
                    s35=Sum('he_35'),
                    s100=Sum('he_100'),
                )
            )

            # Compensaciones CHE
            try:
                from asistencia.models import PapeletaPermiso
                che_map = defaultdict(Decimal)
                for p in PapeletaPermiso.objects.filter(
                    importacion=imp,
                    tipo_permiso='COMPENSACION_HE',
                    estado='APROBADA',
                    personal__isnull=False,
                ).values('personal_id', 'dias_solicitados'):
                    che_map[p['personal_id']] += Decimal(str(p['dias_solicitados'] or 0))
            except Exception:
                che_map = defaultdict(Decimal)

            to_update = []
            to_create = []

            for row in resumen:
                pid   = row['personal_id']
                s25   = row['s25']  or CERO
                s35   = row['s35']  or CERO
                s100  = row['s100'] or CERO
                total = s25 + s35 + s100
                comp  = che_map.get(pid, CERO)
                saldo = total - comp

                try:
                    banco = BancoHoras.objects.get(
                        personal_id=pid, periodo_anio=anio, periodo_mes=mes)
                    old = (banco.he_25_acumuladas, banco.he_35_acumuladas,
                           banco.he_100_acumuladas, banco.saldo_horas)
                    new = (s25, s35, s100, saldo)
                    if old != new:
                        if verbosity >= 2:
                            self.stdout.write(
                                f'    PID={pid} | '
                                f'100%:{float(old[2]):.2f}→{float(s100):.2f}  '
                                f'saldo:{float(old[3]):.2f}→{float(saldo):.2f}')
                        if not dry_run:
                            banco.he_25_acumuladas  = s25
                            banco.he_35_acumuladas  = s35
                            banco.he_100_acumuladas = s100
                            banco.he_compensadas    = comp
                            banco.saldo_horas       = saldo
                            to_update.append(banco)
                        b_act += 1

                except BancoHoras.DoesNotExist:
                    if verbosity >= 2:
                        self.stdout.write(
                            f'    PID={pid} | NUEVO | saldo={float(saldo):.2f}h')
                    if not dry_run:
                        to_create.append(BancoHoras(
                            personal_id=pid, periodo_anio=anio, periodo_mes=mes,
                            he_25_acumuladas=s25, he_35_acumuladas=s35,
                            he_100_acumuladas=s100, he_compensadas=comp,
                            saldo_horas=saldo,
                        ))
                    b_new += 1

            if not dry_run:
                with transaction.atomic():
                    if to_update:
                        BancoHoras.objects.bulk_update(
                            to_update,
                            ['he_25_acumuladas', 'he_35_acumuladas',
                             'he_100_acumuladas', 'he_compensadas', 'saldo_horas'],
                            batch_size=200,
                        )
                    if to_create:
                        BancoHoras.objects.bulk_create(to_create, batch_size=200)

        return b_act, b_new

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        solo_tareo = options['solo_tareo']
        solo_banco = options['solo_banco']
        verbosity  = options['verbosity']

        try:
            fecha_ini = date.fromisoformat(options['fecha_ini'])
            fecha_fin = date.fromisoformat(options['fecha_fin'])
        except ValueError as e:
            raise CommandError(f'Fecha inválida: {e}')

        config = ConfiguracionSistema.get()
        prefix = '[DRY-RUN] ' if dry_run else ''

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{prefix}FIX DOMINGOS + FERIADOS — {fecha_ini} → {fecha_fin}'))
        self.stdout.write(
            f'  Regla LOCAL/LIMA domingo : horas_normales=0, todas→he_100\n'
            f'  Regla feriado (cualquier): horas_normales=0, todas→he_100\n'
            f'  Regla FORÁNEO domingo    : normal≤{config.jornada_domingo_horas}h, exceso→he_100\n'
        )

        # ── Paso 1: RegistroTareo ─────────────────────────────────────────────
        t_act = t_sin = t_err = 0
        personal_set = set()

        if not solo_banco:
            self._sep()
            self.stdout.write(self.style.MIGRATE_HEADING('PASO 1 — RegistroTareo'))

            # Filtro: domingos LOCAL/LIMA  OR  feriados (cualquier condición)
            qs = (
                RegistroTareo.objects
                .filter(
                    fecha__gte=fecha_ini,
                    fecha__lte=fecha_fin,
                )
                .filter(
                    Q(dia_semana=6, condicion__in=['LOCAL', 'LIMA']) |
                    Q(es_feriado=True)
                )
                .select_related('personal')
                .order_by('fecha', 'condicion', 'dni')
            )

            total = qs.count()
            self.stdout.write(f'  Registros candidatos: {total:,}')

            if total == 0:
                self.stdout.write(self.style.WARNING(
                    '  ⚠ Sin registros en el rango. Verificar fechas.'))
            else:
                t_act, t_sin, t_err, personal_set = self._fix_registros(
                    qs, config, dry_run, verbosity)

                sym = '✓' if not dry_run else '→'
                if t_act:
                    self.stdout.write(self.style.SUCCESS(
                        f'  {sym} Con cambios    : {t_act:,}'))
                else:
                    self.stdout.write(f'  {sym} Con cambios    : {t_act:,}')
                self.stdout.write(f'    Sin cambio     : {t_sin:,}')
                if t_err:
                    self.stderr.write(self.style.ERROR(f'    Errores        : {t_err}'))

        # ── Paso 2: BancoHoras ────────────────────────────────────────────────
        b_act = b_new = 0

        if not solo_tareo:
            self._sep()
            self.stdout.write(self.style.MIGRATE_HEADING('PASO 2 — BancoHoras'))
            b_act, b_new = self._fix_banco(fecha_ini, fecha_fin, dry_run, verbosity)

            sym = '✓' if not dry_run else '→'
            if b_act or b_new:
                self.stdout.write(self.style.SUCCESS(
                    f'  {sym} Actualizados : {b_act:,}'))
                if b_new:
                    self.stdout.write(self.style.SUCCESS(
                        f'  {sym} Creados      : {b_new:,}'))
            else:
                self.stdout.write('  Sin cambios en BancoHoras.')

        # ── Resumen ───────────────────────────────────────────────────────────
        self._sep('═')
        self.stdout.write(self.style.MIGRATE_HEADING(f'{prefix}RESUMEN FINAL'))
        self.stdout.write(
            f'  RegistroTareo modificados : {t_act:,}\n'
            f'  RegistroTareo sin cambio  : {t_sin:,}\n'
            f'  Errores                   : {t_err}\n'
            f'  Personal únicos afectados : {len(personal_set):,}\n'
            f'  BancoHoras actualizados   : {b_act:,}\n'
            f'  BancoHoras creados        : {b_new:,}'
        )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n  ⚠ DRY-RUN activo — ningún dato fue modificado.\n'
                '  Ejecutar sin --dry-run para aplicar los cambios.'))
        elif t_act or b_act or b_new:
            self.stdout.write(self.style.SUCCESS('\n  ✓ Corrección completada exitosamente.'))
        else:
            self.stdout.write('\n  No hubo cambios que aplicar.')
