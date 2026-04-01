"""
Management command to populate Cargo.funciones with standard job functions.
Usage: python manage.py seed_cargos
"""
from django.core.management.base import BaseCommand
from personal.models import Cargo


# Funciones por cargo para sector construcción/ingeniería
# Basado en contratos reales de obra (Hospital Antonio Lorena - Cusco)
FUNCIONES_POR_CARGO = {
    'Residente de Obra': [
        'Desarrollar y ejecutar la estrategia de entrega con el director del proyecto.',
        'Trabajar estrechamente con el cliente, el contratante y los equipos involucrados para garantizar una entrega exitosa y oportuna.',
        'Preparar los informes que se enviarán al cliente, asegurándose de que todos los documentos se entreguen a tiempo.',
        'Cumplir con el contrato con el cliente en todo momento.',
        'Entregar los trabajos de acuerdo con el contrato y la información de obras.',
        'Coordinar entre los subcontratistas de diseño e instalación para asegurar la coordinación oportuna de cada subcontrato.',
        'Seguir las instrucciones del supervisor de calidad durante la entrega de las obras.',
        'Gestionar el equipo de supervisión del sitio.',
        'Emitir alertas tempranas sobre asuntos con implicaciones de demora, costo o rendimiento.',
        'Cooperar en reuniones de alerta temprana y reducción de riesgos.',
        'Asegurar que una estrategia de comunicación efectiva esté en su lugar.',
        'Garantizar las aprobaciones oportunamente para avanzar en todos los asuntos relacionados con las obras.',
        'Liderar el capital humano del consorcio.',
        'Desarrollar toda su capacidad de trabajo en el desempeño de las labores principales, conexas y complementarias inherentes al puesto.',
        'Respetar las normativas y políticas internas del empleador.',
    ],
    'Director de Proyecto': [
        'Dirigir la planificación, ejecución y cierre del proyecto de obra.',
        'Supervisar el cumplimiento del contrato con el cliente.',
        'Gestionar el presupuesto y controlar los costos del proyecto.',
        'Coordinar con las gerencias funcionales para garantizar recursos adecuados.',
        'Representar al consorcio ante el cliente y entidades reguladoras.',
        'Tomar decisiones estratégicas sobre el avance del proyecto.',
        'Aprobar cambios de alcance, cronograma y presupuesto.',
        'Supervisar al residente de obra y gerentes funcionales.',
    ],
    'Gerente General': [
        'Dirigir y representar legalmente a la empresa o consorcio.',
        'Definir la estrategia empresarial y objetivos corporativos.',
        'Supervisar todas las gerencias funcionales.',
        'Aprobar presupuestos, inversiones y decisiones estratégicas.',
        'Gestionar relaciones con clientes, socios y entidades gubernamentales.',
        'Velar por el cumplimiento normativo y legal de la organización.',
    ],
    'Gerente de Administración y Finanzas': [
        'Dirigir la gestión financiera, contable y administrativa del proyecto.',
        'Supervisar tesorería, contabilidad, presupuestos y recursos humanos.',
        'Elaborar y controlar el flujo de caja y estados financieros.',
        'Gestionar relaciones con entidades bancarias y financieras.',
        'Asegurar el cumplimiento de obligaciones tributarias y laborales.',
        'Aprobar pagos a proveedores y subcontratistas.',
    ],
    'Ingeniero de Costos': [
        'Elaborar y mantener actualizado el presupuesto del proyecto.',
        'Realizar análisis de costos unitarios y partidas presupuestales.',
        'Controlar y reportar desviaciones de costos vs. presupuesto.',
        'Elaborar valorizaciones mensuales de avance de obra.',
        'Analizar productividad y proponer optimizaciones de costo.',
        'Coordinar con planeamiento y producción para proyecciones de gasto.',
    ],
    'Ingeniero de Planeamiento': [
        'Elaborar y actualizar el cronograma maestro del proyecto.',
        'Coordinar con las áreas y especialidades las actividades del programa intermedio y plan semanal.',
        'Controlar el avance en campo y mantener los cronogramas actualizados.',
        'Preparar informes de avance y análisis de ruta crítica.',
        'Identificar restricciones y proponer acciones correctivas.',
        'Aplicar metodologías de planificación (Last Planner, Lean Construction).',
    ],
    'Asistente de Planeamiento': [
        'Elaborar y actualizar el cronograma del proyecto en coordinación con otras áreas de trabajo.',
        'Coordinar y elaborar con las áreas y especialidades las actividades a incluir en el programa intermedio y plan semanal.',
        'Control de avance en campo y mantenimiento de cronogramas del proyecto.',
        'Desarrollar toda su capacidad de trabajo en el desempeño de las labores principales, conexas y complementarias inherentes al puesto.',
        'Respetar las normativas y políticas internas del empleador.',
    ],
    'Jefe de Recursos Humanos': [
        'Dirigir la gestión del talento humano del proyecto.',
        'Supervisar procesos de selección, contratación y desvinculación.',
        'Gestionar la planilla, beneficios sociales y relaciones laborales.',
        'Asegurar el cumplimiento de la normativa laboral peruana.',
        'Coordinar programas de capacitación y desarrollo.',
        'Administrar contratos laborales, prórrogas y adendas.',
    ],
    'Analista de Recursos Humanos': [
        'Gestionar procesos de selección y reclutamiento de personal.',
        'Administrar expedientes de personal y documentación laboral.',
        'Elaborar contratos, prórrogas y adendas laborales.',
        'Controlar asistencia, permisos y vacaciones del personal.',
        'Apoyar en la elaboración de planillas y liquidaciones.',
        'Gestionar trámites ante ESSALUD, AFP/ONP y MTPE.',
    ],
    'Ingeniero de Calidad': [
        'Implementar y supervisar el sistema de gestión de calidad en obra.',
        'Elaborar y revisar protocolos de control de calidad.',
        'Realizar inspecciones y ensayos de materiales y procesos constructivos.',
        'Gestionar no conformidades y acciones correctivas.',
        'Coordinar con laboratorio para ensayos de control de calidad.',
        'Elaborar dossieres de calidad para entrega al cliente.',
    ],
    'Supervisor de SSOMA': [
        'Supervisar el cumplimiento de normas de seguridad y salud en el trabajo.',
        'Realizar inspecciones diarias de seguridad en frentes de obra.',
        'Investigar accidentes e incidentes de trabajo.',
        'Capacitar al personal en temas de seguridad, salud ocupacional y medio ambiente.',
        'Elaborar el plan de seguridad y salud del proyecto.',
        'Gestionar permisos de trabajo de alto riesgo (PETAR).',
    ],
    'Jefe SSOMA': [
        'Dirigir el sistema de gestión de seguridad, salud ocupacional y medio ambiente.',
        'Elaborar y supervisar el Plan de Seguridad y Salud en el Trabajo.',
        'Gestionar la matriz de identificación de peligros y evaluación de riesgos (IPERC).',
        'Coordinar con el Comité de Seguridad y Salud en el Trabajo.',
        'Supervisar el cumplimiento de la Ley 29783 y su reglamento.',
        'Gestionar incidentes, accidentes y enfermedades ocupacionales.',
    ],
    'Contador': [
        'Gestionar la contabilidad general y analítica del proyecto.',
        'Elaborar estados financieros mensuales y anuales.',
        'Controlar el cumplimiento de obligaciones tributarias (SUNAT).',
        'Supervisar la facturación, cuentas por cobrar y pagar.',
        'Coordinar auditorías internas y externas.',
        'Elaborar reportes financieros para la gerencia.',
    ],
    'Asistente Administrativo': [
        'Apoyar en la gestión administrativa y documentaria del proyecto.',
        'Gestionar correspondencia, archivos y documentación.',
        'Coordinar logística de oficina y requerimientos de suministros.',
        'Elaborar informes y reportes administrativos.',
        'Apoyar en la coordinación de reuniones y eventos.',
        'Gestionar trámites documentarios internos y externos.',
    ],
    'Capataz': [
        'Supervisar directamente las cuadrillas de trabajo en campo.',
        'Distribuir tareas y controlar la productividad del personal a cargo.',
        'Verificar el cumplimiento de especificaciones técnicas.',
        'Controlar el uso adecuado de materiales y herramientas.',
        'Reportar avance diario al ingeniero de producción.',
        'Asegurar el cumplimiento de normas de seguridad en su frente de trabajo.',
    ],
    'Topógrafo': [
        'Realizar levantamientos topográficos y replanteo de obra.',
        'Controlar niveles, alineamientos y cotas de la construcción.',
        'Elaborar planos topográficos y de replanteo.',
        'Verificar conformidad de trazos con los planos de diseño.',
        'Mantener y calibrar equipos topográficos.',
        'Documentar y reportar información topográfica del proyecto.',
    ],
    'Conductor de Vehiculo Liviano': [
        'Conducir vehículos asignados para transporte de personal y materiales.',
        'Realizar inspecciones diarias del vehículo (check list).',
        'Mantener el vehículo en condiciones óptimas de operación.',
        'Cumplir con las normas de tránsito y seguridad vial.',
        'Reportar incidencias y necesidades de mantenimiento vehicular.',
        'Gestionar documentación del vehículo (SOAT, revisión técnica, tarjeta de propiedad).',
    ],
}


class Command(BaseCommand):
    help = 'Poblar funciones por cargo para cargos de construcción/ingeniería'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sobrescribir funciones existentes',
        )

    def handle(self, *args, **options):
        force = options['force']
        updated = 0
        skipped = 0

        for cargo_nombre, funciones in FUNCIONES_POR_CARGO.items():
            funciones_text = '\n'.join(funciones)
            try:
                cargo = Cargo.objects.get(nombre__iexact=cargo_nombre)
            except Cargo.DoesNotExist:
                # Try partial match
                matches = Cargo.objects.filter(nombre__icontains=cargo_nombre.split()[0])
                if cargo_nombre == 'Capataz':
                    matches = Cargo.objects.filter(nombre__istartswith='Capataz')
                if not matches.exists():
                    self.stdout.write(self.style.WARNING(f'  Cargo no encontrado: {cargo_nombre}'))
                    continue
                # Apply to all matches
                for cargo in matches:
                    if cargo.funciones and not force:
                        skipped += 1
                        continue
                    cargo.funciones = funciones_text
                    cargo.save(update_fields=['funciones'])
                    updated += 1
                    self.stdout.write(f'  + {cargo.nombre}')
                continue

            if cargo.funciones and not force:
                skipped += 1
                continue

            cargo.funciones = funciones_text
            cargo.save(update_fields=['funciones'])
            updated += 1
            self.stdout.write(f'  + {cargo.nombre}')

        self.stdout.write(self.style.SUCCESS(
            f'\nResultado: {updated} actualizados, {skipped} omitidos (ya tenían funciones)'
        ))
