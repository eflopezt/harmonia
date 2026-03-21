"""
Corrección de horas para personal LOCAL/LIMA — ciclo 21-Feb al 21-Mar 2026.

Problema: _obtener_jornada() usaba Personal.jornada_horas (default=8) en vez de
  config.jornada_local_horas (8.5 lun–vie) y config.jornada_sabado_horas (5.5 sáb).
  Además, el descuento de almuerzo (0.5h) se aplicaba en sábado, dando 5.0 en vez de 5.5.

Uso:
    python manage.py fix_jornada_local_mar2026
    python manage.py fix_jornada_local_mar2026 --dry-run    # solo muestra cambios
    python manage.py fix_jornada_local_mar2026 --fecha-ini 2026-02-21 --fecha-fin 2026-03-21
"""
import logging
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from asistencia.models import RegistroTareo, ConfiguracionSistema

logger = logging.getLogger(__name__)

CERO = Decimal('0')

# Códigos que NO generan horas normales ni HE (igual que en processor.py)
CODIGOS_SIN_HE = {
    'DL', 'DLA', 'CHE', 'VAC', 'DM', 'LCG', 'LF',
    'LP', 'LSG', 'FA', 'TR', 'CDT', 'CPF', 'FR', 'ATM', 'SAI',
}


def _jornada_local(config, dia_semana: int) -> Decimal:
    """Jornada correcta para LOCAL/LIMA según día de semana."""
    if dia_semana == 5:          # sábado
        return Decimal(str(config.jornada_sabado_horas))
    return Decimal(str(config.jornada_local_horas))


def _recalcular(codigo: str, horas_marcadas, jornada_h: Decimal,
                es_feriado: bool, dia_semana: int):
    """
    Replica la lógica de processor._calcular_horas() con los valores correctos.
    Retorna (horas_efectivas, horas_normales, he_25, he_35, he_100).
    """
    # SS (sin salida): presente pero sin marca de salida → paga jornada completa
    es_ss = (codigo == 'SS')
    if es_ss:
        return jornada_h, jornada_h, CERO, CERO, CERO

    # Códigos sin horas
    if codigo in CODIGOS_SIN_HE or not horas_marcadas or horas_marcadas <= CERO:
        return CERO, CERO, CERO, CERO, CERO

    horas_marcadas = Decimal(str(horas_marcadas))

    # Descuento almuerzo
    if jornada_h > Decimal('9'):
        # FORÁNEO: almuerzo incluido
        horas_ef = horas_marcadas
    elif jornada_h <= Decimal('6'):
        # Jornada corta (sábado 5.5h): sin break de almuerzo
        horas_ef = horas_marcadas
    else:
        # LOCAL lun–vie: descontar 0.5h si marcó más de 5h
        almuerzo = Decimal('0.5') if horas_marcadas > 5 else CERO
        horas_ef = max(CERO, horas_marcadas - almuerzo)

    if horas_ef <= CERO:
        return CERO, CERO, CERO, CERO, CERO

    # Feriado laborado o descanso semanal (domingo=6): todo al 100%
    es_descanso_semanal = (dia_semana == 6)
    if es_feriado or es_descanso_semanal:
        return horas_ef, CERO, CERO, CERO, horas_ef

    # Día normal
    if horas_ef <= jornada_h:
        return horas_ef, horas_ef, CERO, CERO, CERO

    # Horas extra
    exceso = horas_ef - jornada_h
    if exceso <= Decimal('2'):
        he25 = exceso
        he35 = CERO
    else:
        he25 = Decimal('2')
        he35 = exceso - Decimal('2')

    return horas_ef, jornada_h, he25, he35, CERO


class Command(BaseCommand):
    help = (
        'Corrige horas_normales/HE para personal LOCAL/LIMA del ciclo Feb21–Mar21 2026. '
        'Aplica jornada correcta: 8.5h lun–vie, 5.5h sábado.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra los cambios sin escribir en BD.')
        parser.add_argument(
            '--fecha-ini', default='2026-02-21',
            help='Inicio del ciclo (default: 2026-02-21).')
        parser.add_argument(
            '--fecha-fin', default='2026-03-21',
            help='Fin del ciclo (default: 2026-03-21).')
        parser.add_argument(
            '--condicion', default='LOCAL,LIMA',
            help='Condiciones a corregir separadas por coma (default: LOCAL,LIMA).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        try:
            fecha_ini = date.fromisoformat(options['fecha_ini'])
            fecha_fin = date.fromisoformat(options['fecha_fin'])
        except ValueError as e:
            raise CommandError(f'Fecha inválida: {e}')

        condiciones = [c.strip().upper() for c in options['condicion'].split(',')]

        # Config del sistema
        config = ConfiguracionSistema.get()
        jornada_lv  = Decimal(str(config.jornada_local_horas))    # 8.5
        jornada_sab = Decimal(str(config.jornada_sabado_horas))   # 5.5

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"[DRY-RUN] " if dry_run else ""}Corrección jornada LOCAL '
            f'{fecha_ini} → {fecha_fin}'
        ))
        self.stdout.write(
            f'  Jornada Lun–Vie : {jornada_lv}h\n'
            f'  Jornada Sábado  : {jornada_sab}h\n'
            f'  Condiciones     : {condiciones}\n'
        )

        qs = RegistroTareo.objects.filter(
            fecha__gte=fecha_ini,
            fecha__lte=fecha_fin,
            condicion__in=condiciones,
        ).select_related('personal').order_by('fecha', 'dni')

        total = qs.count()
        self.stdout.write(f'  Registros encontrados: {total}\n')

        if total == 0:
            self.stdout.write(self.style.WARNING('  Sin registros. Verificar fechas/condición.'))
            return

        actualizados = 0
        sin_cambio   = 0
        errores      = 0
        a_actualizar = []

        dias_semana = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']

        for reg in qs.iterator(chunk_size=500):
            try:
                jornada_h = _jornada_local(config, reg.dia_semana)

                h_ef, h_norm, he25, he35, he100 = _recalcular(
                    codigo=reg.codigo_dia or '',
                    horas_marcadas=reg.horas_marcadas,
                    jornada_h=jornada_h,
                    es_feriado=reg.es_feriado,
                    dia_semana=reg.dia_semana,
                )

                # ¿Cambió algo?
                changed = (
                    reg.horas_efectivas != h_ef   or
                    reg.horas_normales  != h_norm  or
                    reg.he_25           != he25    or
                    reg.he_35           != he35    or
                    reg.he_100          != he100
                )

                if not changed:
                    sin_cambio += 1
                    continue

                nombre = (reg.personal.apellidos_nombres
                          if reg.personal else reg.nombre_archivo or reg.dni)
                ds = dias_semana[reg.dia_semana] if 0 <= reg.dia_semana <= 6 else '?'

                self.stdout.write(
                    f'  {reg.fecha} {ds} | {reg.codigo_dia:<6} | {nombre[:35]:<35} | '
                    f'n: {float(reg.horas_normales or 0):4.1f}→{float(h_norm):4.1f}  '
                    f'25%: {float(reg.he_25 or 0):4.1f}→{float(he25):4.1f}  '
                    f'jornada: {float(jornada_h):.1f}h'
                )

                if not dry_run:
                    reg.horas_efectivas = h_ef
                    reg.horas_normales  = h_norm
                    reg.he_25           = he25
                    reg.he_35           = he35
                    reg.he_100          = he100
                    a_actualizar.append(reg)

                actualizados += 1

            except Exception as e:
                errores += 1
                self.stderr.write(
                    f'  ERROR en registro {reg.pk} ({reg.fecha} {reg.dni}): {e}')

        # Guardar en bloque
        if not dry_run and a_actualizar:
            with transaction.atomic():
                RegistroTareo.objects.bulk_update(
                    a_actualizar,
                    ['horas_efectivas', 'horas_normales', 'he_25', 'he_35', 'he_100'],
                    batch_size=200,
                )

        # Resumen final
        self.stdout.write('\n' + '─' * 70)
        style = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(style(
            f'{"[DRY-RUN] " if dry_run else ""}Resultado:\n'
            f'  Con cambios    : {actualizados}\n'
            f'  Sin cambio     : {sin_cambio}\n'
            f'  Errores        : {errores}\n'
            f'  TOTAL revisados: {total}'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n  → Ejecutar sin --dry-run para aplicar los cambios.'))
        elif actualizados > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n  ✓ {actualizados} registros corregidos en BD.'))
