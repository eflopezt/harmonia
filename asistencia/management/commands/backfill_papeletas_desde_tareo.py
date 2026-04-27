"""
Backfill: crear papeletas faltantes para los RegistroTareo que ya tienen un
código de permiso/licencia/compensación pero no tienen RegistroPapeleta
asociado.

Usado tras introducir el auto-sync inverso (matriz → papeleta), para
regularizar los días editados antes del cambio.

Lógica:
  - Recorre RegistroTareo con codigo_dia en CODIGO_A_TIPO.
  - Salta los que ya están vinculados (papeleta_ref no vacío) o cubiertos
    por una papeleta APROBADA/EJECUTADA del mismo tipo.
  - Agrupa días consecutivos del mismo personal y mismo código en una sola
    papeleta (rango fecha_inicio..fecha_fin).
  - Crea papeleta APROBADA, origen=SISTEMA. Marca el RegistroTareo con
    fuente=PAPELETA y papeleta_ref=PAP#{id}.
  - Omite días en períodos CERRADOS.

Uso:
    python manage.py backfill_papeletas_desde_tareo
    python manage.py backfill_papeletas_desde_tareo --fecha-ini 2026-03-22 --fecha-fin 2026-04-21
    python manage.py backfill_papeletas_desde_tareo --personal 123
    python manage.py backfill_papeletas_desde_tareo --dry-run
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from asistencia.models import RegistroPapeleta, RegistroTareo
from asistencia.services.papeletas_sync import CODIGO_A_TIPO


class Command(BaseCommand):
    help = ('Crea papeletas faltantes para RegistroTareo con código de '
            'permiso/licencia/compensación sin papeleta asociada.')

    def add_arguments(self, parser):
        parser.add_argument('--fecha-ini', help='YYYY-MM-DD (inclusive)')
        parser.add_argument('--fecha-fin', help='YYYY-MM-DD (inclusive)')
        parser.add_argument('--personal', type=int, help='Filtrar por personal_id')
        parser.add_argument('--dry-run', action='store_true',
                            help='No crea nada, solo reporta.')

    def handle(self, *args, **opts):
        from cierre.models import PeriodoCierre

        dry = opts['dry_run']
        f_ini = date.fromisoformat(opts['fecha_ini']) if opts['fecha_ini'] else None
        f_fin = date.fromisoformat(opts['fecha_fin']) if opts['fecha_fin'] else None
        personal_id = opts['personal']

        cerrados = set(
            PeriodoCierre.objects.filter(estado='CERRADO')
            .values_list('anio', 'mes')
        )

        qs = (RegistroTareo.objects
              .filter(codigo_dia__in=CODIGO_A_TIPO.keys(),
                      personal__isnull=False)
              .exclude(papeleta_ref__startswith='PAP#')
              .select_related('personal')
              .order_by('personal_id', 'codigo_dia', 'fecha'))

        if f_ini:
            qs = qs.filter(fecha__gte=f_ini)
        if f_fin:
            qs = qs.filter(fecha__lte=f_fin)
        if personal_id:
            qs = qs.filter(personal_id=personal_id)

        candidatos = []
        for r in qs.iterator(chunk_size=500):
            if (r.fecha.year, r.fecha.month) in cerrados:
                continue
            tipo = CODIGO_A_TIPO.get(r.codigo_dia)
            if not tipo:
                continue
            if RegistroPapeleta.objects.filter(
                personal=r.personal,
                tipo_permiso=tipo,
                estado__in=['APROBADA', 'EJECUTADA'],
                fecha_inicio__lte=r.fecha,
                fecha_fin__gte=r.fecha,
            ).exists():
                continue
            candidatos.append(r)

        self.stdout.write(f'Candidatos sin papeleta: {len(candidatos)}')
        if not candidatos:
            self.stdout.write(self.style.SUCCESS('Nada que hacer.'))
            return

        rangos = list(_agrupar_rangos(candidatos))
        self.stdout.write(f'Rangos a crear: {len(rangos)}')

        if dry:
            for personal, codigo, ini, fin, regs in rangos[:50]:
                self.stdout.write(
                    f'  [DRY] {personal.apellidos_nombres} ({personal.nro_doc}) '
                    f'{codigo} {ini}..{fin} ({len(regs)} días)'
                )
            if len(rangos) > 50:
                self.stdout.write(f'  ... y {len(rangos) - 50} rangos más')
            self.stdout.write(self.style.WARNING('DRY RUN - no se guardó nada.'))
            return

        creadas = 0
        regs_actualizados = 0
        with transaction.atomic():
            for personal, codigo, ini, fin, regs in rangos:
                tipo = CODIGO_A_TIPO[codigo]
                area_nombre = ''
                if getattr(personal, 'subarea_id', None):
                    try:
                        area_nombre = personal.subarea.area.nombre
                    except Exception:
                        area_nombre = ''
                pap = RegistroPapeleta.objects.create(
                    personal=personal,
                    dni=getattr(personal, 'nro_doc', '') or '',
                    nombre_archivo=getattr(personal, 'apellidos_nombres', '') or '',
                    tipo_permiso=tipo,
                    fecha_inicio=ini,
                    fecha_fin=fin,
                    dias_habiles=(fin - ini).days + 1,
                    estado='APROBADA',
                    origen='SISTEMA',
                    fecha_aprobacion=date.today(),
                    observaciones=('Backfill: papeleta generada desde matriz '
                                   'de asistencia (registro previo sin papeleta)'),
                    area_trabajo=area_nombre[:150],
                    cargo=(getattr(personal, 'cargo', '') or '')[:150],
                )
                creadas += 1
                ref = f'PAP#{pap.pk}'
                ids = [r.pk for r in regs]
                regs_actualizados += RegistroTareo.objects.filter(pk__in=ids).update(
                    fuente_codigo='PAPELETA', papeleta_ref=ref,
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Papeletas creadas: {creadas} | '
            f'RegistroTareo vinculados: {regs_actualizados}'
        ))


def _agrupar_rangos(regs):
    """Agrupa registros consecutivos del mismo personal y código en rangos.

    Yields (personal, codigo, fecha_ini, fecha_fin, [registros]).
    Los regs llegan ordenados por personal_id, codigo_dia, fecha.
    """
    if not regs:
        return
    grupo = [regs[0]]
    for r in regs[1:]:
        prev = grupo[-1]
        misma_serie = (
            r.personal_id == prev.personal_id
            and r.codigo_dia == prev.codigo_dia
            and r.fecha == prev.fecha + timedelta(days=1)
        )
        if misma_serie:
            grupo.append(r)
        else:
            yield (grupo[0].personal, grupo[0].codigo_dia,
                   grupo[0].fecha, grupo[-1].fecha, grupo)
            grupo = [r]
    yield (grupo[0].personal, grupo[0].codigo_dia,
           grupo[0].fecha, grupo[-1].fecha, grupo)
