"""
Management command: seed_documentos
Carga categorías y tipos de documento predefinidos para el Legajo Digital.

Uso:
    python manage.py seed_documentos            # crea los que faltan
    python manage.py seed_documentos --clean    # fusiona duplicados + normaliza
    python manage.py seed_documentos --reset    # borra todo y recrea
"""
from django.core.management.base import BaseCommand
from documentos.models import CategoriaDocumento, TipoDocumento


CATEGORIAS = [
    {'nombre': 'Contractual',      'icono': 'fa-file-contract',  'orden': 1},
    {'nombre': 'Identidad',        'icono': 'fa-id-card',        'orden': 2},
    {'nombre': 'Seguridad Social', 'icono': 'fa-shield-alt',     'orden': 3},
    {'nombre': 'SSOMA',            'icono': 'fa-hard-hat',       'orden': 4},
    {'nombre': 'Académico',        'icono': 'fa-graduation-cap', 'orden': 5},
    {'nombre': 'Disciplinario',    'icono': 'fa-gavel',          'orden': 6},
    {'nombre': 'Otros',            'icono': 'fa-folder',         'orden': 7},
]

# Categorías duplicadas conocidas → se fusionan en la canónica
DUPLICADOS = {
    # nombre_duplicado    : nombre_canonico
    'Identificación':      'Identidad',
    'Identificacion':      'Identidad',
    'SSOMA / SST':         'SSOMA',
    'SST':                 'SSOMA',
    'Salud':               'SSOMA',
    'Formación':           'Académico',
    'Formacion':           'Académico',
    'Legal':               'Disciplinario',
}

# Tipos de documento renombrados: nombre_viejo → nombre_nuevo
RENOMBRES_TIPO = {
    'DNI / CE (copia)': 'DNI / CE',
    'DNI (copia)':      'DNI / CE',
}

# (nombre, categoria, obligatorio, vence, dias_alerta, aplica_staff, aplica_rco)
TIPOS = [
    # ── Contractual ──────────────────────────────────────────────────────────
    ('Contrato de Trabajo',              'Contractual',      True,  False, 30, True, True),
    ('Adenda / Addendum',                'Contractual',      False, False, 30, True, True),
    ('Carta de Oferta',                  'Contractual',      False, False, 30, True, True),
    ('Boleta de Pago (última)',          'Contractual',      False, False, 30, True, True),

    # ── Identidad ─────────────────────────────────────────────────────────────
    ('DNI / CE',                         'Identidad',        True,  True,  60, True, True),
    ('RUC (si aplica)',                  'Identidad',        False, False, 30, True, False),
    ('Partida de Nacimiento',            'Identidad',        False, False, 30, True, True),
    ('Partida de Matrimonio',            'Identidad',        False, False, 30, True, True),
    ('Partida de Nacimiento de hijos',   'Identidad',        False, False, 30, True, True),

    # ── Seguridad Social ──────────────────────────────────────────────────────
    ('Declaración AFP / ONP',            'Seguridad Social', True,  False, 30, True, True),
    ('EsSalud - Formulario T-6',         'Seguridad Social', True,  False, 30, True, True),
    ('Constancia de AFP',                'Seguridad Social', False, False, 30, True, True),
    ('SCTR (Seguro Complementario)',     'Seguridad Social', False, True,  30, False, True),

    # ── SSOMA ─────────────────────────────────────────────────────────────────
    ('Examen Médico Pre-ocupacional',    'SSOMA',            True,  True,  60, True, True),
    ('Examen Médico Periódico',          'SSOMA',            True,  True,  30, True, True),
    ('Certificado Altura Geográfica',    'SSOMA',            False, True,  30, False, True),
    ('Inducción SST (constancia)',       'SSOMA',            True,  False, 30, True, True),
    ('IPERC firmado',                    'SSOMA',            False, False, 30, False, True),
    ('ATS - Análisis Trabajo Seguro',    'SSOMA',            False, False, 30, False, True),
    ('EPP - Entrega equipos protección', 'SSOMA',            False, False, 30, True, True),

    # ── Académico ─────────────────────────────────────────────────────────────
    ('CV documentado',                   'Académico',        False, False, 30, True, True),
    ('Título / Grado universitario',     'Académico',        False, False, 30, True, False),
    ('Certificado de estudios',          'Académico',        False, False, 30, True, True),
    ('Certificado de trabajo anterior',  'Académico',        False, False, 30, True, True),
    ('Licencia de conducir',             'Académico',        False, True,  30, False, True),

    # ── Disciplinario ─────────────────────────────────────────────────────────
    ('Antecedentes penales',             'Disciplinario',    True,  True,  30, True, True),
    ('Antecedentes policiales',          'Disciplinario',    True,  True,  30, True, True),
    ('Declaración jurada domicilio',     'Disciplinario',    False, False, 30, True, True),
    ('Reglamento Interno (cargo recibido)', 'Disciplinario', True,  False, 30, True, True),

    # ── Otros ─────────────────────────────────────────────────────────────────
    ('Cuenta bancaria (voucher)',        'Otros',            False, False, 30, True, True),
    ('Referencia personal/laboral',      'Otros',            False, False, 30, True, True),
    ('Fotografía reciente',              'Otros',            False, False, 30, True, True),
]


class Command(BaseCommand):
    help = 'Carga y normaliza categorías y tipos de documento del Legajo Digital.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Borra categorías y tipos existentes antes de crear.',
        )
        parser.add_argument(
            '--clean', action='store_true',
            help='Fusiona duplicados conocidos y normaliza iconos/órdenes.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            TipoDocumento.objects.all().delete()
            CategoriaDocumento.objects.all().delete()
            self.stdout.write(self.style.WARNING('[OK] Categorias y tipos eliminados.'))

        if options['clean']:
            self._clean_duplicates()
            self._rename_tipos()

        self._seed_categorias()
        self._seed_tipos()

    # ─────────────────────────────────────────────────────────────────────────

    def _clean_duplicates(self):
        """Fusiona categorías duplicadas en la canónica y elimina la sobrante."""
        merged = 0
        deleted = 0
        for dup_name, canon_name in DUPLICADOS.items():
            try:
                dup = CategoriaDocumento.objects.get(nombre=dup_name)
            except CategoriaDocumento.DoesNotExist:
                continue

            # Buscar la canónica (puede no existir aún, se crea en _seed_categorias)
            canon, _ = CategoriaDocumento.objects.get_or_create(
                nombre=canon_name,
                defaults={
                    'icono': next(
                        (c['icono'] for c in CATEGORIAS if c['nombre'] == canon_name), 'fa-folder'
                    ),
                    'orden': next(
                        (c['orden'] for c in CATEGORIAS if c['nombre'] == canon_name), 99
                    ),
                    'activa': True,
                },
            )

            # Reasignar tipos que apuntan al duplicado
            count = TipoDocumento.objects.filter(categoria=dup).count()
            TipoDocumento.objects.filter(categoria=dup).update(categoria=canon)
            merged += count

            dup.delete()
            deleted += 1
            self.stdout.write(
                f'  [OK] "{dup_name}" -> "{canon_name}" ({count} tipos reasignados)'
            )

        self.stdout.write(self.style.SUCCESS(
            f'  Limpieza: {deleted} categorias duplicadas eliminadas, {merged} tipos reasignados.'
        ))

    def _rename_tipos(self):
        """Renombra tipos de documento obsoletos y deduplica."""
        for viejo, nuevo in RENOMBRES_TIPO.items():
            updated = TipoDocumento.objects.filter(nombre=viejo).update(nombre=nuevo)
            if updated:
                self.stdout.write(f'  [OK] Tipo renombrado: "{viejo}" -> "{nuevo}"')

        # Deduplicar TipoDocumento por nombre (mantener el mas antiguo)
        from django.db.models import Min
        from django.db.models import Count
        dups = (
            TipoDocumento.objects
            .values('nombre')
            .annotate(cnt=Count('id'), min_id=Min('id'))
            .filter(cnt__gt=1)
        )
        total_del = 0
        for dup in dups:
            deleted, _ = TipoDocumento.objects.filter(
                nombre=dup['nombre']
            ).exclude(id=dup['min_id']).delete()
            total_del += deleted
            self.stdout.write(f'  [OK] Tipos duplicados "{dup["nombre"]}": {deleted} eliminados')
        if total_del:
            self.stdout.write(f'  Tipos deduplicados: {total_del} eliminados.')

    def _seed_categorias(self):
        """Crea o actualiza (icono + orden) las categorías canónicas."""
        cats_creadas = 0
        for c in CATEGORIAS:
            obj, created = CategoriaDocumento.objects.update_or_create(
                nombre=c['nombre'],
                defaults={'icono': c['icono'], 'orden': c['orden'], 'activa': True},
            )
            if created:
                cats_creadas += 1
                self.stdout.write(f'  + Categoria: {obj.nombre}')
            # Si ya existía, update_or_create actualizó icono y orden
        return cats_creadas

    def _seed_tipos(self):
        """Crea los tipos que no existen. No sobreescribe los existentes."""
        cats = {c.nombre: c for c in CategoriaDocumento.objects.all()}
        creados = 0
        existentes = 0
        for (nombre, cat_nombre, oblig, vence, dias, staff, rco) in TIPOS:
            cat = cats.get(cat_nombre)
            _, created = TipoDocumento.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'categoria': cat,
                    'obligatorio': oblig,
                    'vence': vence,
                    'dias_alerta_vencimiento': dias,
                    'aplica_staff': staff,
                    'aplica_rco': rco,
                    'activo': True,
                },
            )
            if created:
                creados += 1
            else:
                existentes += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seed documentos: {len(CATEGORIAS)} categorías · '
            f'{creados} tipos creados · {existentes} ya existían.'
        ))
