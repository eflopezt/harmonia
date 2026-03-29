"""
Management command to seed default contract templates (PlantillaContrato).
Usage: python manage.py seed_plantillas_contrato
"""
from django.core.management.base import BaseCommand
from personal.models import PlantillaContrato


PLANTILLAS = [
    {
        'nombre': 'Contrato a Plazo Fijo',
        'tipo_contrato': 'PLAZO_FIJO',
        'contenido_html': """<div style="font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.6;">
<h2 style="text-align:center;">CONTRATO DE TRABAJO SUJETO A MODALIDAD</h2>
<h3 style="text-align:center;">(A PLAZO FIJO)</h3>

<p>Conste por el presente documento, el contrato de trabajo a plazo fijo que celebran de una parte:</p>

<p><strong>EL EMPLEADOR:</strong> {{empresa}}, con RUC N. {{ruc_empresa}}, con domicilio en {{direccion_empresa}}, debidamente representada por su representante legal;</p>

<p><strong>EL TRABAJADOR:</strong> {{nombre_empleado}}, identificado con DNI N. {{dni}}, con domicilio en ___________________________;</p>

<p>En los terminos y condiciones siguientes:</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR es una empresa que requiere de los servicios del TRABAJADOR para desempenar el cargo de <strong>{{cargo}}</strong>, en virtud de necesidades propias de su actividad.</p>

<h4>SEGUNDA: OBJETO DEL CONTRATO</h4>
<p>Por el presente contrato, EL EMPLEADOR contrata los servicios de EL TRABAJADOR para que desempene el cargo de <strong>{{cargo}}</strong>, debiendo someterse al cumplimiento de las funciones inherentes al puesto.</p>

<h4>TERCERA: DURACION DEL CONTRATO</h4>
<p>El presente contrato tiene una duracion determinada, iniciandose el <strong>{{fecha_inicio}}</strong> y concluyendo el <strong>{{fecha_fin}}</strong>.</p>

<h4>CUARTA: REMUNERACION</h4>
<p>EL EMPLEADOR se obliga a pagar al TRABAJADOR una remuneracion mensual de <strong>S/ {{remuneracion}}</strong> (soles), monto que incluye la remuneracion basica y toda asignacion que por ley corresponda. Dicho monto sera abonado en la oportunidad y forma que establezca EL EMPLEADOR.</p>

<h4>QUINTA: JORNADA DE TRABAJO</h4>
<p>EL TRABAJADOR cumplira una jornada de trabajo de 48 horas semanales, conforme al D.Leg. 854 y su reglamento.</p>

<h4>SEXTA: PERIODO DE PRUEBA</h4>
<p>EL TRABAJADOR estara sujeto a un periodo de prueba de tres (3) meses, de conformidad con lo establecido en el articulo 10 del D.Leg. 728.</p>

<h4>SEPTIMA: OBLIGACIONES DEL TRABAJADOR</h4>
<p>EL TRABAJADOR se compromete a cumplir con las normas propias del centro de trabajo, asi como las contenidas en el Reglamento Interno de Trabajo y las que se impartan por necesidades del servicio.</p>

<h4>OCTAVA: CAUSALES DE RESOLUCION</h4>
<p>Son causales de resolucion del presente contrato las previstas en la legislacion laboral vigente.</p>

<p>Firmado en dos ejemplares de un mismo tenor, en la ciudad de _______________, a los ____ dias del mes de _____________ de 20____.</p>

<br><br>
<table style="width:100%;">
<tr>
<td style="text-align:center; width:50%;">
<br><br>___________________________<br>
<strong>EL EMPLEADOR</strong><br>
{{empresa}}
</td>
<td style="text-align:center; width:50%;">
<br><br>___________________________<br>
<strong>EL TRABAJADOR</strong><br>
{{nombre_empleado}}<br>
DNI: {{dni}}
</td>
</tr>
</table>
</div>""",
    },
    {
        'nombre': 'Contrato Indefinido',
        'tipo_contrato': 'INDEFINIDO',
        'contenido_html': """<div style="font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.6;">
<h2 style="text-align:center;">CONTRATO DE TRABAJO A TIEMPO INDETERMINADO</h2>

<p>Conste por el presente documento, el contrato de trabajo a tiempo indeterminado que celebran de una parte:</p>

<p><strong>EL EMPLEADOR:</strong> {{empresa}}, con RUC N. {{ruc_empresa}}, con domicilio en {{direccion_empresa}}, debidamente representada por su representante legal;</p>

<p><strong>EL TRABAJADOR:</strong> {{nombre_empleado}}, identificado con DNI N. {{dni}}, con domicilio en ___________________________;</p>

<p>En los terminos y condiciones siguientes:</p>

<h4>PRIMERA: OBJETO DEL CONTRATO</h4>
<p>Por el presente contrato, EL EMPLEADOR contrata los servicios de EL TRABAJADOR para que desempene el cargo de <strong>{{cargo}}</strong>, a tiempo indeterminado, debiendo someterse al cumplimiento de las funciones inherentes al puesto.</p>

<h4>SEGUNDA: INICIO DE LA RELACION LABORAL</h4>
<p>La relacion laboral se inicia el <strong>{{fecha_inicio}}</strong>, siendo de duracion indeterminada.</p>

<h4>TERCERA: REMUNERACION</h4>
<p>EL EMPLEADOR se obliga a pagar al TRABAJADOR una remuneracion mensual de <strong>S/ {{remuneracion}}</strong> (soles), monto que incluye la remuneracion basica y toda asignacion que por ley corresponda.</p>

<h4>CUARTA: JORNADA DE TRABAJO</h4>
<p>EL TRABAJADOR cumplira una jornada de trabajo de 48 horas semanales, conforme al D.Leg. 854.</p>

<h4>QUINTA: PERIODO DE PRUEBA</h4>
<p>EL TRABAJADOR estara sujeto a un periodo de prueba de tres (3) meses, conforme al articulo 10 del D.Leg. 728.</p>

<h4>SEXTA: OBLIGACIONES</h4>
<p>EL TRABAJADOR se compromete a cumplir con las normas del centro de trabajo y el Reglamento Interno de Trabajo.</p>

<h4>SEPTIMA: CAUSALES DE EXTINCION</h4>
<p>Son causales de extincion del presente contrato las previstas en el articulo 16 del D.Leg. 728 — Ley de Productividad y Competitividad Laboral.</p>

<p>Firmado en dos ejemplares de un mismo tenor, en la ciudad de _______________, a los ____ dias del mes de _____________ de 20____.</p>

<br><br>
<table style="width:100%;">
<tr>
<td style="text-align:center; width:50%;">
<br><br>___________________________<br>
<strong>EL EMPLEADOR</strong><br>
{{empresa}}
</td>
<td style="text-align:center; width:50%;">
<br><br>___________________________<br>
<strong>EL TRABAJADOR</strong><br>
{{nombre_empleado}}<br>
DNI: {{dni}}
</td>
</tr>
</table>
</div>""",
    },
    {
        'nombre': 'Contrato por Obra o Servicio',
        'tipo_contrato': 'OBRA_SERVICIO',
        'contenido_html': """<div style="font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.6;">
<h2 style="text-align:center;">CONTRATO DE TRABAJO PARA OBRA DETERMINADA O SERVICIO ESPECIFICO</h2>

<p>Conste por el presente documento, el contrato de trabajo para obra determinada o servicio especifico que celebran:</p>

<p><strong>EL EMPLEADOR:</strong> {{empresa}}, con RUC N. {{ruc_empresa}}, con domicilio en {{direccion_empresa}}, debidamente representada por su representante legal;</p>

<p><strong>EL TRABAJADOR:</strong> {{nombre_empleado}}, identificado con DNI N. {{dni}}, con domicilio en ___________________________;</p>

<p>En los terminos y condiciones siguientes:</p>

<h4>PRIMERA: ANTECEDENTES</h4>
<p>EL EMPLEADOR requiere los servicios de personal calificado para la ejecucion de una obra/servicio especifico, conforme al articulo 63 del D.Leg. 728.</p>

<h4>SEGUNDA: OBJETO</h4>
<p>EL TRABAJADOR se compromete a prestar sus servicios en el cargo de <strong>{{cargo}}</strong>, para la ejecucion de la obra o servicio especifico que se detalla: ___________________________.</p>

<h4>TERCERA: PLAZO</h4>
<p>El presente contrato se inicia el <strong>{{fecha_inicio}}</strong> y tendra una duracion equivalente a la que demande la culminacion de la obra o servicio especifico contratado, estimandose como fecha tentativa de conclusion el <strong>{{fecha_fin}}</strong>.</p>

<h4>CUARTA: REMUNERACION</h4>
<p>La remuneracion mensual sera de <strong>S/ {{remuneracion}}</strong> (soles).</p>

<h4>QUINTA: JORNADA DE TRABAJO</h4>
<p>La jornada de trabajo sera de 48 horas semanales.</p>

<h4>SEXTA: OBLIGACIONES</h4>
<p>EL TRABAJADOR se compromete a cumplir con las normas del centro de trabajo.</p>

<p>Firmado en dos ejemplares, en la ciudad de _______________, a los ____ dias del mes de _____________ de 20____.</p>

<br><br>
<table style="width:100%;">
<tr>
<td style="text-align:center; width:50%;">
<br><br>___________________________<br>
<strong>EL EMPLEADOR</strong><br>
{{empresa}}
</td>
<td style="text-align:center; width:50%;">
<br><br>___________________________<br>
<strong>EL TRABAJADOR</strong><br>
{{nombre_empleado}}<br>
DNI: {{dni}}
</td>
</tr>
</table>
</div>""",
    },
]


class Command(BaseCommand):
    help = 'Crea plantillas de contrato predeterminadas (PlantillaContrato)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recrear plantillas aunque ya existan',
        )

    def handle(self, *args, **options):
        force = options['force']
        creadas = 0
        existentes = 0

        for data in PLANTILLAS:
            exists = PlantillaContrato.objects.filter(
                nombre=data['nombre'],
                tipo_contrato=data['tipo_contrato'],
            ).exists()

            if exists and not force:
                existentes += 1
                self.stdout.write(f"  Ya existe: {data['nombre']}")
                continue

            if exists and force:
                PlantillaContrato.objects.filter(
                    nombre=data['nombre'],
                    tipo_contrato=data['tipo_contrato'],
                ).delete()

            PlantillaContrato.objects.create(**data)
            creadas += 1
            self.stdout.write(self.style.SUCCESS(f"  Creada: {data['nombre']}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nPlantillas creadas: {creadas}, ya existentes: {existentes}"
        ))
