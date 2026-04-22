"""
Sincroniza papeletas APROBADAS/EJECUTADAS con sus RegistroTareo.

Útil cuando se crean/modifican papeletas DESPUÉS de importar el tareo:
los días cubiertos por la papeleta quedaron con FA/DS/NA/CPF automático, y
este comando los actualiza al código correcto derivado de la papeleta.

Reglas:
  - Solo toca registros automáticos (FA, DS, NA, CPF, FER) o inexistentes.
  - NO sobrescribe trabajo real (RELOJ con ef>0, MANUAL).
  - Si no existe registro en un día cubierto, lo crea con ef=0, HE=0.

Mapeo tipo_permiso → codigo_dia:
  BAJADAS → DL | VACACIONES → VAC | COMPENSACION_HE → CHE | ...

Uso:
    python manage.py sync_papeletas_registros --fecha-ini 2026-03-22 --fecha-fin 2026-04-21
    python manage.py sync_papeletas_registros --dry-run
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from asistencia.models import RegistroPapeleta, RegistroTareo, TareoImportacion


CERO = Decimal('0')

# Códigos que el sync puede sobrescribir (automáticos).
# RELOJ con ef>0 y MANUAL son intocables.
CODIGOS_AUTO_SOBREESCRIBIBLES = {'FA', 'DS', 'NA', 'CPF', 'FER', 'DL', 'DLA'}

# tipo_permiso → código tareo
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


class Command(BaseCommand):
    help = 'Propaga papeletas APROBADAS/EJECUTADAS a RegistroTareo.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha-ini', help='YYYY-MM-DD (default: todas)')
        parser.add_argument('--fecha-fin', help='YYYY-MM-DD (default: todas)')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        fecha_ini = date.fromisoformat(opts['fecha_ini']) if opts['fecha_ini'] else None
        fecha_fin = date.fromisoformat(opts['fecha_fin']) if opts['fecha_fin'] else None

        paps = RegistroPapeleta.objects.filter(estado__in=['APROBADA', 'EJECUTADA'])
        if fecha_ini and fecha_fin:
            paps = paps.filter(fecha_fin__gte=fecha_ini, fecha_inicio__lte=fecha_fin)

        self.stdout.write(f'Papeletas aprobadas: {paps.count()}')

        # TareoImportacion para trazabilidad (NOT NULL FK)
        imp = None
        if not dry:
            imp = TareoImportacion.objects.create(
                archivo_nombre='sync_papeletas_registros',
                tipo='RELOJ',
                periodo_inicio=fecha_ini or date(2026, 1, 1),
                periodo_fin=fecha_fin or date(2026, 12, 31),
                estado='PROCESANDO',
            )

        stats = {
            'actualizados': 0, 'creados': 0,
            'skip_sin_tipo_mapeo': 0, 'skip_reloj': 0, 'skip_otro': 0,
        }
        cambios_ejemplo = []

        a_crear = []
        a_actualizar_ids = []
        updates_por_codigo = {}  # {codigo: [ids]}

        for pap in paps.select_related('personal'):
            codigo_objetivo = TIPO_A_CODIGO.get(pap.tipo_permiso)
            if not codigo_objetivo:
                stats['skip_sin_tipo_mapeo'] += 1
                continue

            d = pap.fecha_inicio
            if fecha_ini:
                d = max(d, fecha_ini)
            f = pap.fecha_fin
            if fecha_fin:
                f = min(f, fecha_fin)

            while d <= f:
                existente = RegistroTareo.objects.filter(
                    personal=pap.personal, fecha=d,
                ).first()

                if existente is None:
                    # Crear registro con código de la papeleta
                    cond = pap.personal.condicion or 'LOCAL'
                    grupo = pap.personal.grupo_tareo or ('STAFF' if cond != 'FORANEO' else 'RCO')
                    a_crear.append(RegistroTareo(
                        importacion=imp,
                        personal=pap.personal,
                        dni=pap.personal.nro_doc,
                        nombre_archivo=pap.personal.apellidos_nombres,
                        grupo=grupo,
                        condicion=cond,
                        fecha=d,
                        dia_semana=d.weekday(),
                        es_feriado=False,
                        codigo_dia=codigo_objetivo,
                        fuente_codigo='PAPELETA',
                        horas_efectivas=CERO,
                        horas_normales=CERO,
                        he_25=CERO, he_35=CERO, he_100=CERO,
                        he_al_banco=(grupo == 'STAFF'),
                        papeleta_ref=f'PAP#{pap.pk}',
                    ))
                    stats['creados'] += 1
                    if len(cambios_ejemplo) < 10:
                        cambios_ejemplo.append(f'  + {d} {pap.personal.nro_doc} {codigo_objetivo} (nuevo)')

                elif existente.codigo_dia == codigo_objetivo:
                    pass  # ya está correcto
                elif existente.fuente_codigo == 'RELOJ' and (existente.horas_efectivas or 0) > 0:
                    # Día trabajado con marca real → no sobreescribir
                    stats['skip_reloj'] += 1
                elif existente.codigo_dia in CODIGOS_AUTO_SOBREESCRIBIBLES:
                    if len(cambios_ejemplo) < 10:
                        cambios_ejemplo.append(
                            f'  ~ {d} {pap.personal.nro_doc} {existente.codigo_dia} → {codigo_objetivo}')
                    updates_por_codigo.setdefault(codigo_objetivo, []).append(existente.pk)
                    stats['actualizados'] += 1
                else:
                    stats['skip_otro'] += 1

                d += timedelta(days=1)

        self.stdout.write(f'\n=== RESUMEN ===')
        for k, v in stats.items():
            self.stdout.write(f'  {k}: {v}')

        self.stdout.write('\nEjemplos:')
        for line in cambios_ejemplo:
            self.stdout.write(line)

        if dry:
            self.stdout.write(self.style.WARNING('\nDRY RUN - no se guardó.'))
            return

        with transaction.atomic():
            if a_crear:
                RegistroTareo.objects.bulk_create(a_crear, batch_size=300)
            for codigo, ids in updates_por_codigo.items():
                RegistroTareo.objects.filter(pk__in=ids).update(
                    codigo_dia=codigo,
                    fuente_codigo='PAPELETA',
                    horas_efectivas=CERO, horas_normales=CERO,
                    he_25=CERO, he_35=CERO, he_100=CERO,
                )
            if imp:
                imp.estado = 'COMPLETADO'
                imp.registros_ok = stats['creados'] + stats['actualizados']
                imp.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Actualizados {stats["actualizados"]}, creados {stats["creados"]}.'
        ))
