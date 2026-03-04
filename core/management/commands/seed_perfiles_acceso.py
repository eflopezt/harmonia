"""
Seed para perfiles de acceso predefinidos (RBAC).

Uso:
    python manage.py seed_perfiles_acceso
    python manage.py seed_perfiles_acceso --reset   # Borra y recrea todos

Perfiles creados:
  ADMIN_RRHH    — Administrador RRHH: acceso total excepto configuración
  JEFE_AREA     — Jefe de Área: módulos operativos de su área
  CONSULTOR     — Consultor / Solo lectura: analytics + reportes
  EMPLEADO      — Empleado: solo portal de autoservicio (sin admin)
"""
from django.core.management.base import BaseCommand
from core.models import PerfilAcceso


PERFILES = [
    # ── Administrador RRHH ───────────────────────────────────────────────
    {
        'codigo': 'admin-rrhh',
        'nombre': 'Administrador RRHH',
        'descripcion': (
            'Acceso completo a todos los módulos de RRHH. '
            'Puede aprobar solicitudes y exportar datos. '
            'No tiene acceso a Configuración del Sistema (exclusivo superusuario).'
        ),
        'es_sistema': True,
        # Módulos: todo activado excepto configuracion
        'mod_personal':       True,
        'mod_asistencia':     True,
        'mod_vacaciones':     True,
        'mod_documentos':     True,
        'mod_capacitaciones': True,
        'mod_disciplinaria':  True,
        'mod_evaluaciones':   True,
        'mod_encuestas':      True,
        'mod_salarios':       True,
        'mod_reclutamiento':  True,
        'mod_prestamos':      True,
        'mod_viaticos':       True,
        'mod_onboarding':     True,
        'mod_calendario':     True,
        'mod_analytics':      True,
        'mod_configuracion':  False,   # Solo superusuario
        'mod_roster':         True,
        'puede_aprobar':      True,
        'puede_exportar':     True,
    },

    # ── Jefe de Área ─────────────────────────────────────────────────────
    {
        'codigo': 'jefe-area',
        'nombre': 'Jefe de Área',
        'descripcion': (
            'Acceso a módulos operativos de su área: personal a cargo, '
            'asistencia, vacaciones, permisos, evaluaciones, capacitaciones, '
            'roster y calendario. Sin acceso a módulos financieros ni analíticos.'
        ),
        'es_sistema': True,
        'mod_personal':       True,
        'mod_asistencia':     True,
        'mod_vacaciones':     True,
        'mod_documentos':     True,
        'mod_capacitaciones': True,
        'mod_disciplinaria':  False,
        'mod_evaluaciones':   True,
        'mod_encuestas':      True,
        'mod_salarios':       False,
        'mod_reclutamiento':  False,
        'mod_prestamos':      False,
        'mod_viaticos':       False,
        'mod_onboarding':     False,
        'mod_calendario':     True,
        'mod_analytics':      False,
        'mod_configuracion':  False,
        'mod_roster':         True,
        'puede_aprobar':      True,
        'puede_exportar':     True,
    },

    # ── Consultor / Solo lectura ──────────────────────────────────────────
    {
        'codigo': 'consultor',
        'nombre': 'Consultor / Solo lectura',
        'descripcion': (
            'Perfil de análisis y reportería. Puede ver dashboards, '
            'analytics y módulos principales pero no puede aprobar ni '
            'crear registros. Ideal para gerentes que solo necesitan KPIs.'
        ),
        'es_sistema': True,
        'mod_personal':       True,
        'mod_asistencia':     True,
        'mod_vacaciones':     True,
        'mod_documentos':     True,
        'mod_capacitaciones': True,
        'mod_disciplinaria':  False,
        'mod_evaluaciones':   True,
        'mod_encuestas':      True,
        'mod_salarios':       False,
        'mod_reclutamiento':  False,
        'mod_prestamos':      False,
        'mod_viaticos':       False,
        'mod_onboarding':     False,
        'mod_calendario':     True,
        'mod_analytics':      True,
        'mod_configuracion':  False,
        'mod_roster':         False,
        'puede_aprobar':      False,
        'puede_exportar':     True,
    },

    # ── Empleado (solo portal) ────────────────────────────────────────────
    {
        'codigo': 'empleado',
        'nombre': 'Empleado',
        'descripcion': (
            'Perfil base para trabajadores. Solo puede acceder al portal '
            'de autoservicio (mis datos, mis asistencias, mis vacaciones, '
            'mis documentos). No tiene acceso a ningún módulo de administración.'
        ),
        'es_sistema': True,
        # Todos los módulos admin desactivados — el portal tiene su propio control
        'mod_personal':       False,
        'mod_asistencia':     False,
        'mod_vacaciones':     False,
        'mod_documentos':     False,
        'mod_capacitaciones': False,
        'mod_disciplinaria':  False,
        'mod_evaluaciones':   False,
        'mod_encuestas':      True,   # Puede responder encuestas
        'mod_salarios':       False,
        'mod_reclutamiento':  False,
        'mod_prestamos':      False,
        'mod_viaticos':       False,
        'mod_onboarding':     False,
        'mod_calendario':     True,   # Puede ver el calendario
        'mod_analytics':      False,
        'mod_configuracion':  False,
        'mod_roster':         False,
        'puede_aprobar':      False,
        'puede_exportar':     False,
    },
]


class Command(BaseCommand):
    help = 'Crea o actualiza los perfiles de acceso predefinidos del sistema.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Borra y recrea todos los perfiles de sistema.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            borrados = PerfilAcceso.objects.filter(es_sistema=True).delete()
            self.stdout.write(self.style.WARNING(f'Borrados {borrados[0]} perfiles de sistema.'))

        creados    = 0
        actualizados = 0

        for datos in PERFILES:
            codigo = datos.pop('codigo')
            perfil, created = PerfilAcceso.objects.update_or_create(
                codigo=codigo,
                defaults=datos,
            )
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  [+] Creado: {perfil.nombre} ({codigo})'))
            else:
                actualizados += 1
                self.stdout.write(f'  [~] Actualizado: {perfil.nombre} ({codigo})')

            # Restaurar el código en el dict para no mutarlo (por si se llama dos veces)
            datos['codigo'] = codigo

        self.stdout.write(
            self.style.SUCCESS(
                f'\nListo: {creados} perfiles creados, {actualizados} actualizados.'
            )
        )
        self.stdout.write(
            '\nAsigna perfiles en: Admin > Core > Perfiles de Acceso\n'
            'o desde la ficha de Personal > Perfil de Acceso.'
        )
