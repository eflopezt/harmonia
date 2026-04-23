"""
Corrige compensaciones mal aplicadas en 02/04/2026 (Jueves Santo — feriado).

Problema detectado: algunos trabajadores tienen código de compensación
(CPF, CDT, CHE, CT) el 02/04 en vez de en 04/04 (sábado laborable FA).

Corrección:
  02/04 (feriado)  →  FER (ef=norm=HE=0, es_feriado=True)
  04/04 (FA actual) ←  código original de 02/04 (CPF/CDT/CHE/CT)

Además:
  - Unifica FR → FER en toda la tabla RegistroTareo (cualquier fecha).
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from asistencia.models import RegistroTareo


CERO = Decimal('0')
COMP_CODES = {'CPF', 'CDT', 'CHE', 'CT'}


class Command(BaseCommand):
    help = 'Mueve compensaciones 02/04→04/04 y unifica FR→FER en RegistroTareo.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts['dry_run']
        fer_jue = date(2026, 4, 2)
        comp_sab = date(2026, 4, 4)

        # ─── 1. Mover compensaciones 02/04 → 04/04 ────────────────────────
        regs_02 = list(
            RegistroTareo.objects.filter(
                fecha=fer_jue, codigo_dia__in=COMP_CODES,
            ).select_related('personal')
        )
        self.stdout.write(
            f'Trabajadores con compensación ({", ".join(sorted(COMP_CODES))}) en 02/04: {len(regs_02)}')

        movidos = 0
        for r02 in regs_02:
            r04 = RegistroTareo.objects.filter(
                personal_id=r02.personal_id, fecha=comp_sab,
            ).first()
            if not r04:
                self.stdout.write(self.style.WARNING(
                    f'  [saltado] {r02.dni} {r02.personal.apellidos_nombres[:35]} — sin registro 04/04'))
                continue

            codigo_orig = r02.codigo_dia
            self.stdout.write(
                f'  {r02.dni} {r02.personal.apellidos_nombres[:35]:35s} '
                f'02/04:{codigo_orig} → FER | 04/04:{r04.codigo_dia} → {codigo_orig}')

            if not dry:
                # 04/04 recibe el código de compensación
                r04.codigo_dia = codigo_orig
                r04.fuente_codigo = 'COMPENSACION'
                r04.horas_efectivas = CERO
                r04.horas_normales = CERO
                r04.he_25 = CERO
                r04.he_35 = CERO
                r04.he_100 = CERO
                r04.save(update_fields=[
                    'codigo_dia', 'fuente_codigo', 'horas_efectivas',
                    'horas_normales', 'he_25', 'he_35', 'he_100',
                ])
                # 02/04 queda como FER
                r02.codigo_dia = 'FER'
                r02.fuente_codigo = 'FERIADO'
                r02.horas_efectivas = CERO
                r02.horas_normales = CERO
                r02.he_25 = CERO
                r02.he_35 = CERO
                r02.he_100 = CERO
                r02.es_feriado = True
                r02.save(update_fields=[
                    'codigo_dia', 'fuente_codigo', 'horas_efectivas',
                    'horas_normales', 'he_25', 'he_35', 'he_100', 'es_feriado',
                ])
            movidos += 1

        # ─── 2. Unificar FR → FER en toda la tabla ────────────────────────
        qs_fr = RegistroTareo.objects.filter(codigo_dia='FR')
        n_fr = qs_fr.count()
        self.stdout.write(f'\nRegistros con codigo_dia=FR (todas las fechas): {n_fr}')
        if n_fr and not dry:
            qs_fr.update(codigo_dia='FER', fuente_codigo='FERIADO', es_feriado=True)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Movidos {movidos}/{len(regs_02)} compensaciones | '
            f'FR→FER: {n_fr}{" (DRY RUN)" if dry else ""}'))
