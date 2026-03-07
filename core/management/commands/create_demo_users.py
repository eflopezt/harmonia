"""
create_demo_users.py
Crea/actualiza los usuarios de demo para pruebas en Render:

  ADMIN       | admin       | Harmoni2026!  | Superusuario RRHH completo
  TRABAJADOR  | trabajador  | Demo2026!     | Portal empleado (vinculado a empleado real)

Idempotente: se puede ejecutar varias veces sin duplicar.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

USUARIOS_DEMO = [
    # (username, password, email, is_staff, is_superuser, descripcion)
    (
        'admin',
        'Harmoni2026!',
        'admin@harmoni.app',
        True, True,
        'Administrador RRHH - acceso total al sistema',
    ),
    (
        'trabajador',
        'Demo2026!',
        'trabajador@harmoni.app',
        False, False,
        'Empleado demo - acceso al Portal del Colaborador',
    ),
]


class Command(BaseCommand):
    help = 'Crea usuarios de demo para pruebas (admin + trabajador)'

    def handle(self, *args, **options):
        self.stdout.write('\n=== Usuarios de Demo ===\n')

        for username, password, email, is_staff, is_superuser, desc in USUARIOS_DEMO:
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(
                    email=email,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                    is_active=True,
                    first_name=username.capitalize(),
                ),
            )
            # Siempre actualizar password y flags (por si ya existia con otro pass)
            user.set_password(password)
            user.is_staff      = is_staff
            user.is_superuser  = is_superuser
            user.is_active     = True
            user.save()

            estado = 'CREADO' if created else 'ACTUALIZADO'
            self.stdout.write(
                f'  [{estado}] {username} / {password}'
                f'  ({desc})'
            )

        # Vincular 'trabajador' a un empleado real si aun no tiene vinculo
        self._vincular_empleado()

        self.stdout.write('\n--- Credenciales de acceso ---')
        self.stdout.write('  URL: https://harmoni-v19e.onrender.com')
        self.stdout.write('  ADMIN    -> usuario: admin      | pass: Harmoni2026!')
        self.stdout.write('  EMPLEADO -> usuario: trabajador | pass: Demo2026!')
        self.stdout.write('')

    def _vincular_empleado(self):
        """
        Vincula el usuario 'trabajador' al empleado con más datos reales:
        asistencia, historial salarial, vacaciones y préstamos.
        Prioridad: DNI 47110375 (CRUZADO LOLOY ANCELMO) — 186 registros tareo.
        Fallback: primer activo con más registros de tareo.
        """
        try:
            from personal.models import Personal
            from django.db.models import Count

            user = User.objects.get(username='trabajador')

            # Desvincular empleado anterior si existe (para poder reasignar)
            if hasattr(user, 'personal_data') and user.personal_data:
                anterior = user.personal_data
                # Si ya es el empleado con datos, no hacer nada
                if anterior.nro_doc == '47110375':
                    self.stdout.write(
                        f'  [OK] trabajador ya vinculado a: {anterior.apellidos_nombres}'
                    )
                    return
                # Desvincular anterior para reasignar al correcto
                anterior.usuario = None
                anterior.save()

            # 1. Intentar el empleado preferido (mayor cantidad de datos)
            empleado = Personal.objects.filter(
                nro_doc='47110375', estado='Activo'
            ).first()

            # 2. Fallback: el activo con más registros de tareo
            if not empleado:
                empleado = (
                    Personal.objects
                    .filter(estado='Activo', usuario__isnull=True)
                    .annotate(n=Count('registros_tareo'))
                    .order_by('-n')
                    .first()
                )

            if not empleado:
                self.stdout.write('  [WARN] No hay empleados activos disponibles')
                return

            empleado.usuario = user
            empleado.save()
            self.stdout.write(
                f'  [OK] trabajador vinculado a: {empleado.apellidos_nombres} '
                f'(DNI: {empleado.nro_doc}, Cargo: {empleado.cargo})'
            )
        except Exception as e:
            self.stdout.write(f'  [WARN] No se pudo vincular empleado: {e}')
