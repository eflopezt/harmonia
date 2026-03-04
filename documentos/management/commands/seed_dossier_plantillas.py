"""
Management command: seed_dossier_plantillas
Carga plantillas de dossier documentario predefinidas para el sector
construccion, mineria y servicios en Peru.

Uso:
    python manage.py seed_dossier_plantillas
    python manage.py seed_dossier_plantillas --reset
"""
from django.core.management.base import BaseCommand
from documentos.models import PlantillaDossier, PlantillaDossierItem, TipoDocumento


# Estructura: (nombre_plantilla, tipo, descripcion, [(seccion, tipo_doc_nombre, obligatorio, instruccion), ...])
PLANTILLAS = [

    # ─────────────────────────────────────────────────────────────────────────
    # 1. DOSSIER OBRA MINERA / CONSTRUCCION (SSOMA)
    # Requerido por: DS 005-2012-TR, Ley 29783, ISO 45001
    # ─────────────────────────────────────────────────────────────────────────
    (
        'Dossier SSOMA - Obra / Proyecto',
        'PROYECTO',
        'Documentacion de seguridad y salud ocupacional requerida para '
        'trabajadores en obra. Segun DS 005-2012-TR y Ley 29783.',
        [
            ('I. Identificacion',    'DNI / CE',                           True,  'Vigente al ingreso a obra'),
            ('I. Identificacion',    'Partida de Nacimiento',              False, ''),
            ('II. Contractual',      'Contrato de Trabajo',                True,  'Firmado por ambas partes'),
            ('II. Contractual',      'Reglamento Interno (cargo recibido)',True,  'Con firma y fecha del trabajador'),
            ('III. Seguridad Social',u'Declaraci\xf3n AFP / ONP',          True,  'Vigente - formulario T-7 o equivalente AFP'),
            ('III. Seguridad Social','EsSalud - Formulario T-6',           True,  'Acreditar cobertura EsSalud activa'),
            ('III. Seguridad Social','SCTR (Seguro Complementario)',       True,  u'P\xf3liza vigente durante la obra'),
            ('IV. SSOMA',            u'Examen M\xe9dico Pre-ocupacional',  True,  u'Apto para el puesto - no mayor a 2 a\xf1os'),
            ('IV. SSOMA',            u'Inducci\xf3n SST (constancia)',     True,  u'M\xednimo 8 horas segun DS 005-2012-TR'),
            ('IV. SSOMA',            'IPERC firmado',                      True,  u'Espec\xedfico al puesto y \xe1rea'),
            ('IV. SSOMA',            u'ATS - An\xe1lisis Trabajo Seguro',  True,  'Generado el dia de inicio'),
            ('IV. SSOMA',            u'EPP - Entrega equipos protecci\xf3n',True, 'Registro con firma del trabajador'),
            ('IV. SSOMA',            u'Certificado Altura Geogr\xe1fica',  False, u'Requerido si la obra supera 3,000 msnm'),
        ],
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # 2. DOSSIER LICITACION OSCE
    # Requerido por: Ley 30225 (Ley de Contrataciones del Estado)
    # ─────────────────────────────────────────────────────────────────────────
    (
        'Dossier RRHH - Licitacion OSCE',
        'LICITACION',
        'Expediente de personal tecnico para propuestas en licitaciones '
        'publicas. Segun Ley 30225 y bases estandar OSCE.',
        [
            ('I. Perfil Profesional', 'CV documentado',                      True,  'Formato OSCE o libre - firmado con respaldos'),
            ('I. Perfil Profesional', u'T\xedtulo / Grado universitario',    True,  'Copia certificada o fedateada'),
            ('I. Perfil Profesional', 'Certificado de estudios',             False, 'Solo si el cargo lo requiere'),
            ('I. Perfil Profesional', 'Licencia de conducir',                False, 'Para puestos que lo requieran'),
            ('II. Identificacion',    'DNI / CE',                            True,  'Vigente'),
            ('III. Experiencia',      'Certificado de trabajo anterior',     True,  'Acredita experiencia en el cargo'),
            ('IV. Habilitacion',      'Antecedentes penales',                True,  'No mayor a 3 meses'),
            ('IV. Habilitacion',      'Antecedentes policiales',             True,  'No mayor a 3 meses'),
            ('IV. Habilitacion',      u'Declaraci\xf3n jurada domicilio',    True,  ''),
            ('V. Beneficios',         'Cuenta bancaria (voucher)',           True,  'Para pago de honorarios'),
        ],
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # 3. DOSSIER AUDITORIA ISO 45001 / OHSAS
    # ─────────────────────────────────────────────────────────────────────────
    (
        'Dossier Auditoria ISO 45001',
        'AUDITORIA',
        'Evidencias documentales de gestion de SST por trabajador, '
        'requeridas en auditorias de certificacion ISO 45001.',
        [
            ('Registro de Ingreso',  'DNI / CE',                           True,  ''),
            ('Registro de Ingreso',  'Contrato de Trabajo',                True,  ''),
            ('Registro de Ingreso',  u'Declaraci\xf3n AFP / ONP',          True,  ''),
            ('Registro de Ingreso',  'EsSalud - Formulario T-6',           True,  ''),
            ('SST - Ingreso',        u'Examen M\xe9dico Pre-ocupacional',  True,  'Resultado: Apto'),
            ('SST - Ingreso',        u'Inducci\xf3n SST (constancia)',     True,  'Firmada por trabajador y supervisor'),
            (u'SST - Continuo',      u'Examen M\xe9dico Peri\xf3dico',    True,  u'Anual segun DS 005-2012-TR Art. 36'),
            (u'SST - Continuo',      'IPERC firmado',                      True,  'Revisado y firmado por el trabajador'),
            (u'SST - Continuo',      u'EPP - Entrega equipos protecci\xf3n',True, u'Registro hist\xf3rico de entregas'),
            ('Formacion',            'Certificado de estudios',            False, u'Acreditaci\xf3n de formaci\xf3n continua'),
            ('Disciplinario',        'Reglamento Interno (cargo recibido)',True,  u'Evidencia de difusi\xf3n del RISST'),
        ],
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # 4. DOSSIER LEGAJO COMPLETO (Ingreso de Personal)
    # Para nuevos ingresos - archivado en legajo fisico/digital
    # ─────────────────────────────────────────────────────────────────────────
    (
        'Legajo Completo - Ingreso de Personal',
        'INTERNO',
        'Expediente documentario completo para nuevos ingresos. '
        'Incluye documentos de identidad, contractual, previsional y SSOMA.',
        [
            ('Identidad',            'DNI / CE',                           True,  u'Vigente - copia a color'),
            ('Identidad',            'Partida de Nacimiento',              False, 'Para hijos y estado civil'),
            ('Identidad',            'Partida de Matrimonio',              False, 'Si aplica'),
            ('Identidad',            'Partida de Nacimiento de hijos',     False, u'Para asignaci\xf3n familiar'),
            ('Contractual',          'Contrato de Trabajo',                True,  'Original firmado por ambas partes'),
            ('Contractual',          'Carta de Oferta',                    False, 'Si se emitio'),
            ('Contractual',          'Reglamento Interno (cargo recibido)',True,  'Cargo de recepcion firmado'),
            ('Previsional',          u'Declaraci\xf3n AFP / ONP',          True,  'T-7 AFP o declaracion ONP'),
            ('Previsional',          'EsSalud - Formulario T-6',           True,  ''),
            ('Previsional',          'Constancia de AFP',                  False, u'Acredita afiliaci\xf3n'),
            ('Academico',            'CV documentado',                     True,  ''),
            ('Academico',            u'T\xedtulo / Grado universitario',   False, 'Si el cargo lo requiere'),
            ('Academico',            'Licencia de conducir',               False, u'Si el cargo lo requiere - vigente'),
            ('SSOMA',                u'Examen M\xe9dico Pre-ocupacional',  True,  'Apto para el puesto'),
            ('SSOMA',                u'Inducci\xf3n SST (constancia)',     True,  ''),
            ('Habilitacion',         'Antecedentes penales',               True,  'No mayor a 3 meses'),
            ('Habilitacion',         'Antecedentes policiales',            True,  'No mayor a 3 meses'),
            ('Habilitacion',         u'Declaraci\xf3n jurada domicilio',   True,  ''),
            ('Financiero',           'Cuenta bancaria (voucher)',           True,  'Para abono de remuneracion'),
            ('Adicional',            u'Fotograf\xeda reciente',             False, 'Para fotocheck'),
        ],
    ),
]


class Command(BaseCommand):
    help = 'Carga plantillas de dossier documentario predefinidas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Elimina todas las plantillas antes de crear.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            PlantillaDossier.objects.all().delete()
            self.stdout.write('Plantillas eliminadas.')

        # Cache de TipoDocumento por nombre
        tipos_cache = {t.nombre: t for t in TipoDocumento.objects.all()}

        plantillas_creadas = 0
        items_creados = 0
        items_no_encontrados = []

        for (nombre, tipo, desc, items) in PLANTILLAS:
            plantilla, created = PlantillaDossier.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'tipo': tipo,
                    'descripcion': desc,
                    'activa': True,
                    'creado_por': None,
                },
            )
            if created:
                plantillas_creadas += 1
                self.stdout.write(f'  + Plantilla: {nombre}')

            for orden, (seccion, tipo_nombre, oblig, instruccion) in enumerate(items, start=1):
                tipo_doc = tipos_cache.get(tipo_nombre)
                if not tipo_doc:
                    # Intentar busqueda parcial
                    for k, v in tipos_cache.items():
                        if tipo_nombre.lower() in k.lower():
                            tipo_doc = v
                            break
                if not tipo_doc:
                    items_no_encontrados.append(f'  FALTANTE: "{tipo_nombre}" en "{nombre}"')
                    continue

                _, item_created = PlantillaDossierItem.objects.get_or_create(
                    plantilla=plantilla,
                    tipo_documento=tipo_doc,
                    defaults={
                        'seccion': seccion,
                        'orden': orden,
                        'obligatorio': oblig,
                        'instruccion': instruccion,
                    },
                )
                if item_created:
                    items_creados += 1

        if items_no_encontrados:
            self.stdout.write(self.style.WARNING(
                'Tipos de documento no encontrados (ejecuta seed_documentos primero):'
            ))
            for msg in items_no_encontrados:
                self.stdout.write(self.style.WARNING(msg))

        self.stdout.write(self.style.SUCCESS(
            f'Seed dossier: {plantillas_creadas} plantillas creadas, '
            f'{items_creados} items creados.'
        ))
