"""
Redondea horas_efectivas, horas_normales, he_25, he_35, he_100 al múltiplo
más cercano de 0.5 (ROUND_HALF_UP) en todos los RegistroTareo.

Solo toca registros que tengan al menos un campo fuera del múltiplo de 0.5.
No modifica horas_marcadas (valor bruto del reloj).

Uso:
  python manage.py redondear_horas_media --dry-run          # Ver cambios
  python manage.py redondear_horas_media                    # Aplicar
  python manage.py redondear_horas_media --desde 2026-04-01 # Solo desde fecha
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from asistencia.models import RegistroTareo
from asistencia.services.processor import redondear_media_hora


CAMPOS = ['horas_efectivas', 'horas_normales', 'he_25', 'he_35', 'he_100']


def es_no_redondeado(valor):
    if valor is None:
        return False
    # múltiplo de 0.5 ⇔ (valor*10) % 5 == 0
    return (Decimal(valor) * 10) % 5 != 0


class Command(BaseCommand):
    help = 'Redondea horas_efectivas, horas_normales, he_25/35/100 al múltiplo de 0.5.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='No guarda cambios, solo muestra impacto.')
        parser.add_argument('--desde', type=str, default=None,
                            help='Filtrar fecha >= YYYY-MM-DD (opcional).')
        parser.add_argument('--hasta', type=str, default=None,
                            help='Filtrar fecha <= YYYY-MM-DD (opcional).')
        parser.add_argument('--limite', type=int, default=None,
                            help='Máximo de registros a mostrar en dry-run (ejemplos).')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        desde = _parse_fecha(opts['desde']) if opts['desde'] else None
        hasta = _parse_fecha(opts['hasta']) if opts['hasta'] else None
        limite = opts['limite'] or 10

        qs = RegistroTareo.objects.all()
        if desde:
            qs = qs.filter(fecha__gte=desde)
        if hasta:
            qs = qs.filter(fecha__lte=hasta)

        # Filtro SQL: MOD numérico (NO ::int, que trunca: 9.53*10=95 → falso OK).
        # Detecta cualquier decimal distinto de .0 o .5.
        where_or = ' OR '.join(
            f"(MOD(({c} * 10)::numeric, 5) != 0 AND {c} IS NOT NULL AND {c} > 0)"
            for c in CAMPOS
        )
        qs = qs.extra(where=[where_or])

        total = qs.count()
        self.stdout.write(f'Registros a redondear: {total}')
        if total == 0:
            return

        ejemplos_mostrados = 0
        a_actualizar = []
        for r in qs.iterator(chunk_size=500):
            antes = {c: getattr(r, c) for c in CAMPOS}
            despues = {c: redondear_media_hora(antes[c]) for c in CAMPOS}
            if antes == despues:
                continue  # ya estaba redondeado pese al match SQL (caso borde)

            for c, v in despues.items():
                setattr(r, c, v)
            a_actualizar.append(r)

            if ejemplos_mostrados < limite:
                diffs = ', '.join(
                    f'{c}: {antes[c]} → {despues[c]}'
                    for c in CAMPOS if antes[c] != despues[c]
                )
                self.stdout.write(f'  {r.fecha} {r.dni}  {diffs}')
                ejemplos_mostrados += 1

        self.stdout.write(f'\nTotal registros con cambios: {len(a_actualizar)}')

        if dry:
            self.stdout.write(self.style.WARNING('DRY RUN - no se guardó nada.'))
            return

        with transaction.atomic():
            RegistroTareo.objects.bulk_update(a_actualizar, CAMPOS, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f'✓ Actualizados {len(a_actualizar)} registros.'
        ))


def _parse_fecha(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise CommandError(f'Fecha inválida "{s}": {e}')
