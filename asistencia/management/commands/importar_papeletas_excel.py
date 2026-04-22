"""
Importa papeletas desde el formato PermisosLicencias_Personal.xlsx.

Columnas esperadas:
  TipoPermiso | DNI | Personal | Area Trabajo | Cargo | Iniciales |
  FechaInicio | FechaFin | Detalle

Acción:
  - Reemplaza papeletas origen='IMPORTACION' cuyo rango se intersecta con el
    --fecha-ini/--fecha-fin pedido.
  - Crea las papeletas del archivo que caigan en ese rango.
  - No toca papeletas origen='SISTEMA' ni 'PORTAL'.
  - Todas importadas se crean como APROBADA.

Uso:
  python manage.py importar_papeletas_excel /tmp/PermisosLicencias.xlsx \\
      --fecha-ini 2026-03-22 --fecha-fin 2026-04-21
"""
from datetime import date
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from asistencia.models import RegistroPapeleta, TareoImportacion
from asistencia.services.processor import TIPO_PERMISO_MAP
from personal.models import Personal


# Mapeo de Iniciales → tipo_permiso interno (fallback cuando TipoPermiso
# no coincide con el diccionario texto).
INICIALES_TIPO = {
    'B': 'BAJADAS',
    'BA': 'BAJADAS_ACUMULADAS',
    'V': 'VACACIONES',
    'VAC': 'VACACIONES',
    'DM': 'DESCANSO_MEDICO',
    'CHE': 'COMPENSACION_HE',
    'LCG': 'LICENCIA_CON_GOCE',
    'ATM': 'LICENCIA_CON_GOCE',
    'LSG': 'LICENCIA_SIN_GOCE',
    'LF': 'LICENCIA_FALLECIMIENTO',
    'LP': 'LICENCIA_PATERNIDAD',
    'LM': 'LICENCIA_MATERNIDAD',
    'CT': 'COMISION_TRABAJO',
    'TR': 'COMISION_TRABAJO',
    'CPF': 'COMPENSACION_FERIADO',
    'CDT': 'COMP_DIA_TRABAJO',
    'SAI': 'SUSPENSION_ACTO_INSEGURO',
    'SUS': 'SUSPENSION',
    'CAP': 'CAPACITACION',
}


def _norm_key(s: str) -> str:
    if pd.isna(s):
        return ''
    s = str(s).upper().strip()
    for a, b in [('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'),
                 ('Ú', 'U'), ('Ñ', 'N'), ('\ufffd', 'N')]:
        s = s.replace(a, b)
    return s


def _parse_fecha(val):
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Importa papeletas desde PermisosLicencias_Personal.xlsx'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str)
        parser.add_argument('--fecha-ini', required=True,
                            help='YYYY-MM-DD inicio del periodo')
        parser.add_argument('--fecha-fin', required=True,
                            help='YYYY-MM-DD fin del periodo')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        ruta = Path(opts['archivo'])
        if not ruta.exists():
            raise CommandError(f'Archivo no encontrado: {ruta}')
        fecha_ini = date.fromisoformat(opts['fecha_ini'])
        fecha_fin = date.fromisoformat(opts['fecha_fin'])
        dry = opts['dry_run']

        df = pd.read_excel(ruta, sheet_name='Sheet', dtype=str)
        df['DNI'] = df['DNI'].astype(str).str.strip()
        df['_ini'] = df['FechaInicio'].map(_parse_fecha)
        df['_fin'] = df['FechaFin'].map(_parse_fecha)
        df['_iniciales'] = df['Iniciales'].astype(str).str.upper().str.strip()
        df['_tipo_raw'] = df['TipoPermiso'].map(_norm_key)

        # Filtrar al rango: papeletas que se intersecan con [fecha_ini, fecha_fin]
        df_rango = df[
            (df['_fin'] >= fecha_ini) & (df['_ini'] <= fecha_fin)
        ].copy()
        self.stdout.write(
            f'Periodo: {fecha_ini} → {fecha_fin}\n'
            f'Total en archivo: {len(df)} | En rango: {len(df_rango)}'
        )

        # ── 1) Borrar papeletas IMPORTACION del rango ──
        a_borrar = RegistroPapeleta.objects.filter(
            origen='IMPORTACION',
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_ini,
        )
        self.stdout.write(f'Papeletas IMPORTACION a borrar: {a_borrar.count()}')
        if not dry:
            a_borrar.delete()

        # ── 2) Resolver DNIs → Personal ──
        dnis_archivo = set(df_rango['DNI'].tolist())
        personal_map = {p.nro_doc: p for p in Personal.objects.filter(nro_doc__in=dnis_archivo)}
        sin_match = dnis_archivo - set(personal_map.keys())
        if sin_match:
            self.stdout.write(self.style.WARNING(
                f'  DNIs sin match: {len(sin_match)} → {sorted(sin_match)[:5]}…'
            ))

        # ── 3) Crear TareoImportacion ──
        if not dry:
            imp = TareoImportacion.objects.create(
                archivo_nombre=ruta.name,
                periodo_inicio=fecha_ini,
                periodo_fin=fecha_fin,
                estado='PROCESANDO',
            )
            self.stdout.write(f'TareoImportacion #{imp.pk} creada')
        else:
            imp = None

        # ── 4) Crear papeletas ──
        a_crear = []
        stats = {'total': 0, 'sin_match': 0, 'sin_fechas': 0, 'sin_tipo': 0}
        for _, row in df_rango.iterrows():
            dni = row['DNI']
            if dni in sin_match:
                stats['sin_match'] += 1
                continue
            if not row['_ini'] or not row['_fin']:
                stats['sin_fechas'] += 1
                continue
            iniciales = row['_iniciales']
            tipo = TIPO_PERMISO_MAP.get(row['_tipo_raw']) or INICIALES_TIPO.get(iniciales)
            if not tipo:
                stats['sin_tipo'] += 1
                self.stdout.write(self.style.WARNING(
                    f'  Sin tipo: DNI={dni} raw={row["_tipo_raw"]!r} ini={iniciales!r}'
                ))
                continue

            detalle = row.get('Detalle') or ''
            if pd.isna(detalle):
                detalle = ''
            area = row.get('Area Trabajo') or ''
            if pd.isna(area):
                area = ''
            cargo = row.get('Cargo') or ''
            if pd.isna(cargo):
                cargo = ''

            personal = personal_map[dni]
            dias = (row['_fin'] - row['_ini']).days + 1

            a_crear.append(RegistroPapeleta(
                importacion=imp,
                personal=personal,
                dni=dni,
                tipo_permiso=tipo,
                tipo_permiso_raw=str(row['TipoPermiso'])[:150] if not pd.isna(row['TipoPermiso']) else '',
                iniciales=iniciales[:10],
                fecha_inicio=row['_ini'],
                fecha_fin=row['_fin'],
                dias_habiles=dias,
                estado='APROBADA',
                origen='IMPORTACION',
                detalle=str(detalle)[:500],
                area_trabajo=str(area)[:100],
                cargo=str(cargo)[:150],
            ))
            stats['total'] += 1

        self.stdout.write(f'\n=== CREAR ===')
        self.stdout.write(f'A crear: {stats["total"]}')
        self.stdout.write(f'Omitidos sin match DNI: {stats["sin_match"]}')
        self.stdout.write(f'Omitidos sin fechas: {stats["sin_fechas"]}')
        self.stdout.write(f'Omitidos sin tipo: {stats["sin_tipo"]}')

        if dry:
            self.stdout.write(self.style.WARNING('\nDRY RUN - no se guardó nada.'))
            return

        with transaction.atomic():
            RegistroPapeleta.objects.bulk_create(a_crear, batch_size=300)
            imp.estado = 'COMPLETADO'
            imp.registros_ok = stats['total']
            imp.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Importadas {stats["total"]} papeletas.'
        ))
