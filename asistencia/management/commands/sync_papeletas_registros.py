"""
Reconcilia masivamente papeletas → RegistroTareo.

Útil para:
  - Aplicar sync retroactivamente (después de importar tareo).
  - Corregir inconsistencias tras operaciones bulk (bulk_create/update no
    disparan signals).

La lógica está en `asistencia.services.papeletas_sync`. Este comando
itera las papeletas del rango y llama aplicar_papeleta/revertir_papeleta.

Uso:
    python manage.py sync_papeletas_registros
    python manage.py sync_papeletas_registros --fecha-ini 2026-03-22 --fecha-fin 2026-04-21
    python manage.py sync_papeletas_registros --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from asistencia.models import RegistroPapeleta
from asistencia.services.papeletas_sync import (
    aplicar_papeleta, revertir_papeleta, reset_caches,
)


class Command(BaseCommand):
    help = 'Reconcilia papeletas con RegistroTareo masivamente.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha-ini', help='YYYY-MM-DD')
        parser.add_argument('--fecha-fin', help='YYYY-MM-DD')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        fecha_ini = date.fromisoformat(opts['fecha_ini']) if opts['fecha_ini'] else None
        fecha_fin = date.fromisoformat(opts['fecha_fin']) if opts['fecha_fin'] else None

        paps = RegistroPapeleta.objects.all().order_by('personal_id', 'fecha_inicio')
        if fecha_ini and fecha_fin:
            paps = paps.filter(fecha_fin__gte=fecha_ini, fecha_inicio__lte=fecha_fin)

        self.stdout.write(f'Papeletas: {paps.count()}')
        if dry:
            self.stdout.write(self.style.WARNING('DRY RUN - no se guardará nada.'))
            return

        reset_caches()
        totales = {'actualizados': 0, 'creados': 0,
                   'restaurados': 0, 'skip_trabajo_real': 0, 'skip_sin_mapeo': 0}

        with transaction.atomic():
            for pap in paps.iterator(chunk_size=200):
                if pap.estado in ('APROBADA', 'EJECUTADA'):
                    s = aplicar_papeleta(pap)
                else:
                    s = revertir_papeleta(pap)
                for k, v in s.items():
                    totales[k] = totales.get(k, 0) + v

        self.stdout.write(f'\n=== RESUMEN ===')
        for k, v in totales.items():
            self.stdout.write(f'  {k}: {v}')
        self.stdout.write(self.style.SUCCESS('\n✓ Sync completado.'))
