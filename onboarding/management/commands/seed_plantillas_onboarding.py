"""
Comando de management: seed_plantillas_onboarding

Carga en la BD las plantillas por defecto de Onboarding y Offboarding
con sus pasos estándar.

Idempotente: puede ejecutarse varias veces sin duplicar registros.

Uso:
    python manage.py seed_plantillas_onboarding
    python manage.py seed_plantillas_onboarding --force  # sobreescribe si existe
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Carga plantillas por defecto de Onboarding y Offboarding con pasos estándar"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sobreescribir registros existentes',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write(self.style.MIGRATE_HEADING(
            "=== Seed plantillas Onboarding / Offboarding ==="
        ))

        with transaction.atomic():
            self._seed_onboarding(force)
            self._seed_offboarding(force)

        self.stdout.write(self.style.SUCCESS("\nSeed completado exitosamente.\n"))

    def _seed_onboarding(self, force):
        from onboarding.models import PlantillaOnboarding, PasoPlantilla

        self.stdout.write("\n> Plantilla de Onboarding General...")

        nombre = 'Onboarding General'
        plantilla = PlantillaOnboarding.objects.filter(nombre=nombre).first()

        if plantilla and not force:
            self.stdout.write(f"  Ya existe: {nombre} (use --force para sobreescribir)")
            return

        if plantilla and force:
            plantilla.pasos.all().delete()
            self.stdout.write(f"  Sobreescribiendo: {nombre}")
        else:
            plantilla = PlantillaOnboarding.objects.create(
                nombre=nombre,
                descripcion='Plantilla estándar de onboarding para nuevos colaboradores.',
                aplica_grupo='TODOS',
                activa=True,
            )
            self.stdout.write(f"  Creada: {nombre}")

        pasos_data = [
            {
                'orden': 1,
                'titulo': 'Firma de contrato',
                'descripcion': 'Revisar, firmar y archivar el contrato de trabajo.',
                'tipo': 'DOCUMENTO',
                'responsable_tipo': 'RRHH',
                'dias_plazo': 1,
                'obligatorio': True,
            },
            {
                'orden': 2,
                'titulo': 'Creación de correo corporativo',
                'descripcion': 'Crear cuenta de correo electrónico corporativo para el nuevo colaborador.',
                'tipo': 'TAREA',
                'responsable_tipo': 'TI',
                'dias_plazo': 2,
                'obligatorio': True,
            },
            {
                'orden': 3,
                'titulo': 'Entrega de equipo',
                'descripcion': 'Asignar y entregar laptop, celular u otros equipos según el cargo.',
                'tipo': 'TAREA',
                'responsable_tipo': 'TI',
                'dias_plazo': 3,
                'obligatorio': True,
            },
            {
                'orden': 4,
                'titulo': 'Inducción seguridad y salud',
                'descripcion': 'Capacitación obligatoria de inducción en seguridad y salud en el trabajo.',
                'tipo': 'CAPACITACION',
                'responsable_tipo': 'RRHH',
                'dias_plazo': 5,
                'obligatorio': True,
            },
            {
                'orden': 5,
                'titulo': 'Presentación al equipo',
                'descripcion': 'Presentar formalmente al nuevo colaborador con el equipo de trabajo.',
                'tipo': 'TAREA',
                'responsable_tipo': 'JEFE',
                'dias_plazo': 1,
                'obligatorio': True,
            },
            {
                'orden': 6,
                'titulo': 'Configuración de accesos',
                'descripcion': 'Configurar accesos a sistemas, VPN, carpetas compartidas y herramientas.',
                'tipo': 'TAREA',
                'responsable_tipo': 'TI',
                'dias_plazo': 2,
                'obligatorio': True,
            },
            {
                'orden': 7,
                'titulo': 'Capacitación puesto',
                'descripcion': 'Capacitación específica sobre funciones, procesos y herramientas del puesto.',
                'tipo': 'CAPACITACION',
                'responsable_tipo': 'JEFE',
                'dias_plazo': 10,
                'obligatorio': True,
            },
            {
                'orden': 8,
                'titulo': 'Evaluación periodo de prueba',
                'descripcion': 'Evaluación formal al finalizar el periodo de prueba (3 meses).',
                'tipo': 'APROBACION',
                'responsable_tipo': 'JEFE',
                'dias_plazo': 90,
                'obligatorio': True,
            },
        ]

        for data in pasos_data:
            PasoPlantilla.objects.create(plantilla=plantilla, **data)

        self.stdout.write(f"  {len(pasos_data)} pasos creados.")

    def _seed_offboarding(self, force):
        from onboarding.models import PlantillaOffboarding, PasoPlantillaOff

        self.stdout.write("\n> Plantilla de Offboarding General...")

        nombre = 'Offboarding General'
        plantilla = PlantillaOffboarding.objects.filter(nombre=nombre).first()

        if plantilla and not force:
            self.stdout.write(f"  Ya existe: {nombre} (use --force para sobreescribir)")
            return

        if plantilla and force:
            plantilla.pasos.all().delete()
            self.stdout.write(f"  Sobreescribiendo: {nombre}")
        else:
            plantilla = PlantillaOffboarding.objects.create(
                nombre=nombre,
                descripcion='Plantilla estándar de offboarding para desvinculación de colaboradores.',
                activa=True,
            )
            self.stdout.write(f"  Creada: {nombre}")

        pasos_data = [
            {
                'orden': 1,
                'titulo': 'Notificación a TI',
                'descripcion': 'Notificar al área de TI sobre la fecha de cese para planificar revocación de accesos.',
                'tipo': 'NOTIFICACION',
                'responsable_tipo': 'RRHH',
                'dias_plazo': 1,
                'obligatorio': True,
            },
            {
                'orden': 2,
                'titulo': 'Entrega de cargo',
                'descripcion': 'El colaborador entrega formalmente sus funciones, pendientes y documentación al sucesor o jefe.',
                'tipo': 'TAREA',
                'responsable_tipo': 'JEFE',
                'dias_plazo': 5,
                'obligatorio': True,
            },
            {
                'orden': 3,
                'titulo': 'Devolución de equipos',
                'descripcion': 'Recoger laptop, celular, fotocheck, tarjetas de acceso y otros activos asignados.',
                'tipo': 'TAREA',
                'responsable_tipo': 'TI',
                'dias_plazo': 3,
                'obligatorio': True,
            },
            {
                'orden': 4,
                'titulo': 'Liquidación de beneficios',
                'descripcion': 'Calcular y preparar la liquidación de beneficios sociales (CTS, vacaciones, gratificación trunca).',
                'tipo': 'DOCUMENTO',
                'responsable_tipo': 'RRHH',
                'dias_plazo': 15,
                'obligatorio': True,
            },
            {
                'orden': 5,
                'titulo': 'Encuesta de salida',
                'descripcion': 'Realizar entrevista de salida para obtener feedback del colaborador.',
                'tipo': 'TAREA',
                'responsable_tipo': 'RRHH',
                'dias_plazo': 5,
                'obligatorio': False,
            },
            {
                'orden': 6,
                'titulo': 'Revocación de accesos',
                'descripcion': 'Revocar todos los accesos: correo, sistemas, VPN, carpetas, badges.',
                'tipo': 'TAREA',
                'responsable_tipo': 'TI',
                'dias_plazo': 1,
                'obligatorio': True,
            },
        ]

        for data in pasos_data:
            PasoPlantillaOff.objects.create(plantilla=plantilla, **data)

        self.stdout.write(f"  {len(pasos_data)} pasos creados.")
