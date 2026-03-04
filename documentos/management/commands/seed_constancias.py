"""
Seed de Plantillas de Constancias por defecto.

Crea 5 plantillas listas para usar con variables Django y compatible
con el membrete automático de Harmoni.

Uso:
    python manage.py seed_constancias
    python manage.py seed_constancias --reset   # elimina existentes primero
"""
from django.core.management.base import BaseCommand


PLANTILLAS = [
    {
        'nombre': 'Constancia de Trabajo',
        'codigo': 'constancia-trabajo',
        'categoria': 'CONSTANCIA',
        'descripcion': 'Certifica que el trabajador labora actualmente en la empresa.',
        'orden': 1,
        'contenido_html': """<h1>CONSTANCIA DE TRABAJO</h1>

<p class="body-text">
La empresa <strong>{{ empresa.nombre }}</strong>, identificada con RUC {{ empresa.ruc }},
<strong>HACE CONSTAR</strong> que el/la señor(a):
</p>

<table>
    <tr><td class="label">Apellidos y Nombres:</td><td>{{ personal.apellidos_nombres }}</td></tr>
    <tr><td class="label">N&ordm; de Documento:</td><td>{{ personal.nro_doc }}</td></tr>
    <tr><td class="label">Cargo:</td><td>{{ personal.cargo }}</td></tr>
    <tr><td class="label">&Aacute;rea / Sub&Aacute;rea:</td><td>{{ personal.subarea.area.nombre }} / {{ personal.subarea.nombre }}</td></tr>
    <tr><td class="label">Fecha de Ingreso:</td><td>{{ fecha_alta_texto }}</td></tr>
    <tr><td class="label">Tiempo de Servicios:</td><td>{{ antiguedad }}</td></tr>
    <tr><td class="label">R&eacute;gimen Laboral:</td><td>{{ personal.regimen_laboral }}</td></tr>
</table>

<p class="body-text">
Se expide la presente constancia a solicitud del(la) interesado(a), para los fines que
estime conveniente.
</p>
<p class="body-text">Lima, {{ hoy_texto }}.</p>""",
    },
    {
        'nombre': 'Constancia de Ingresos',
        'codigo': 'constancia-ingresos',
        'categoria': 'CONSTANCIA',
        'descripcion': 'Acredita los ingresos mensuales del trabajador (para bancos, alquileres, etc.).',
        'orden': 2,
        'contenido_html': """<h1>CONSTANCIA DE INGRESOS</h1>

<p class="body-text">
La empresa <strong>{{ empresa.nombre }}</strong>, identificada con RUC {{ empresa.ruc }},
<strong>HACE CONSTAR</strong> que el/la trabajador(a):
</p>

<table>
    <tr><td class="label">Apellidos y Nombres:</td><td>{{ personal.apellidos_nombres }}</td></tr>
    <tr><td class="label">N&ordm; de Documento:</td><td>{{ personal.nro_doc }}</td></tr>
    <tr><td class="label">Cargo:</td><td>{{ personal.cargo }}</td></tr>
    <tr><td class="label">Fecha de Ingreso:</td><td>{{ fecha_alta_texto }}</td></tr>
    <tr><td class="label">Tiempo de Servicios:</td><td>{{ antiguedad }}</td></tr>
    <tr><td class="label">Sueldo Mensual:</td><td><strong>S/ {{ personal.sueldo_base }}</strong></td></tr>
    <tr><td class="label">R&eacute;gimen Pensionario:</td><td>{{ personal.get_regimen_pension_display }}</td></tr>
    {% if personal.afp %}<tr><td class="label">AFP:</td><td>{{ personal.afp }}</td></tr>{% endif %}
</table>

<p class="body-text">
Las remuneraciones indicadas corresponden a ingresos de car&aacute;cter regular y permanente,
sujetos a los descuentos de ley establecidos en la legislaci&oacute;n laboral vigente.
</p>
<p class="body-text">
Se expide la presente constancia a solicitud del(la) interesado(a). Lima, {{ hoy_texto }}.
</p>""",
    },
    {
        'nombre': 'Certificado de Trabajo',
        'codigo': 'certificado-trabajo',
        'categoria': 'CERTIFICADO',
        'descripcion': 'Certifica los servicios prestados (al finalizar el vínculo laboral).',
        'orden': 3,
        'contenido_html': """<h1>CERTIFICADO DE TRABAJO</h1>

<p class="body-text">
La empresa <strong>{{ empresa.nombre }}</strong>, identificada con RUC {{ empresa.ruc }},
<strong>CERTIFICA</strong> que el/la señor(a):
</p>

<table>
    <tr><td class="label">Apellidos y Nombres:</td><td>{{ personal.apellidos_nombres }}</td></tr>
    <tr><td class="label">N&ordm; de Documento:</td><td>{{ personal.nro_doc }}</td></tr>
    <tr><td class="label">Cargo desempeñado:</td><td>{{ personal.cargo }}</td></tr>
    <tr><td class="label">Fecha de Ingreso:</td><td>{{ fecha_alta_texto }}</td></tr>
    {% if fecha_cese_texto %}
    <tr><td class="label">Fecha de Cese:</td><td>{{ fecha_cese_texto }}</td></tr>
    {% endif %}
    <tr><td class="label">Tiempo de Servicios:</td><td>{{ antiguedad }}</td></tr>
    <tr><td class="label">R&eacute;gimen Laboral:</td><td>{{ personal.regimen_laboral }}</td></tr>
</table>

<p class="body-text">
Durante el per&iacute;odo laborado, el/la trabajador(a) cumpli&oacute; sus funciones a entera
satisfacci&oacute;n, demostrando responsabilidad, puntualidad y capacidad profesional.
</p>
<p class="body-text">
Se expide el presente certificado a solicitud del(la) interesado(a). Lima, {{ hoy_texto }}.
</p>""",
    },
    {
        'nombre': 'Constancia de Cese',
        'codigo': 'constancia-cese',
        'categoria': 'CONSTANCIA',
        'descripcion': 'Acredita el cese del vínculo laboral y su motivo.',
        'orden': 4,
        'contenido_html': """<h1>CONSTANCIA DE CESE</h1>

<p class="body-text">
La empresa <strong>{{ empresa.nombre }}</strong>, identificada con RUC {{ empresa.ruc }},
<strong>HACE CONSTAR</strong> que el/la señor(a):
</p>

<table>
    <tr><td class="label">Apellidos y Nombres:</td><td>{{ personal.apellidos_nombres }}</td></tr>
    <tr><td class="label">N&ordm; de Documento:</td><td>{{ personal.nro_doc }}</td></tr>
    <tr><td class="label">Cargo:</td><td>{{ personal.cargo }}</td></tr>
    <tr><td class="label">Fecha de Ingreso:</td><td>{{ fecha_alta_texto }}</td></tr>
    <tr><td class="label">Fecha de Cese:</td><td>{{ fecha_cese_texto|default:"&mdash;" }}</td></tr>
    <tr><td class="label">Tiempo de Servicios:</td><td>{{ antiguedad }}</td></tr>
    {% if personal.motivo_cese %}
    <tr><td class="label">Motivo de Cese:</td><td>{{ personal.get_motivo_cese_display }}</td></tr>
    {% endif %}
</table>

<p class="body-text">
Se deja constancia que el v&iacute;nculo laboral qued&oacute; disuelto en la fecha indicada,
habiendo la empresa cumplido con todos los beneficios sociales que establece la ley.
</p>
<p class="body-text">Lima, {{ hoy_texto }}.</p>""",
    },
    {
        'nombre': 'Carta de Presentaci\u00f3n',
        'codigo': 'carta-presentacion',
        'categoria': 'CARTA',
        'descripcion': 'Presenta formalmente al trabajador ante terceros (entidades, clientes, etc.).',
        'orden': 5,
        'contenido_html': """<h1>CARTA DE PRESENTACI&Oacute;N</h1>

<p class="body-text">Lima, {{ hoy_texto }}.</p>

<p class="body-text">
Por medio de la presente, la empresa <strong>{{ empresa.nombre }}</strong> presenta
formalmente al(a la) señor(a) <strong>{{ personal.apellidos_nombres }}</strong>,
identificado(a) con {{ personal.nro_doc }}, quien se desempeña en nuestras
instalaciones como <strong>{{ personal.cargo }}</strong> desde el {{ fecha_alta_texto }}.
</p>

<p class="body-text">
El/La presentado(a) cuenta con plenas facultades para representar a esta empresa en
los asuntos para los cuales ha sido designado(a), por lo que solicitamos se le brinden
las facilidades necesarias para el cumplimiento de sus funciones.
</p>

<p class="body-text">
Agradecemos de antemano las atenciones brindadas al portador de la presente.
</p>

<p class="body-text">Atentamente,</p>""",
    },
]


class Command(BaseCommand):
    help = 'Crea plantillas de constancias por defecto en Harmoni'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina las plantillas del seed antes de recrearlas',
        )

    def handle(self, *args, **options):
        from documentos.models import PlantillaConstancia

        codigos = [p['codigo'] for p in PLANTILLAS]

        if options['reset']:
            deleted, _ = PlantillaConstancia.objects.filter(codigo__in=codigos).delete()
            self.stdout.write(f'  Eliminadas {deleted} plantillas existentes.')

        creadas = 0
        actualizadas = 0

        for data in PLANTILLAS:
            obj, created = PlantillaConstancia.objects.update_or_create(
                codigo=data['codigo'],
                defaults={
                    'nombre': data['nombre'],
                    'categoria': data['categoria'],
                    'descripcion': data['descripcion'],
                    'orden': data['orden'],
                    'contenido_html': data['contenido_html'],
                    'activa': True,
                },
            )
            if created:
                creadas += 1
                self.stdout.write(f'  [+] {obj.nombre}')
            else:
                actualizadas += 1
                self.stdout.write(f'  [=] {obj.nombre} (actualizada)')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeed constancias: {creadas} creadas, {actualizadas} actualizadas.'
            )
        )
