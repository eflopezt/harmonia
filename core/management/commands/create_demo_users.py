"""
create_demo_users.py
Crea/actualiza los usuarios de demo para pruebas en Render:

  ADMIN       | admin       | Harmoni2026!  | Superusuario RRHH completo
  GERENTE     | gerente     | Gerente2026!  | Staff con acceso admin (sin superuser)
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
        'gerente',
        'Gerente2026!',
        'gerente@harmoni.app',
        True, False,
        'Gerente RRHH - acceso staff sin superusuario',
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
    help = 'Crea usuarios de demo para pruebas (admin + gerente + trabajador)'

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

        self._vincular_empleado()
        self._crear_workers_con_dni()

        self.stdout.write('\n--- Credenciales de acceso ---')
        self.stdout.write('  URL: https://harmoni.pe')
        self.stdout.write('  ADMIN    -> usuario: admin      | pass: Harmoni2026!')
        self.stdout.write('  GERENTE  -> usuario: gerente    | pass: Gerente2026!')
        self.stdout.write('  EMPLEADO -> usuario: trabajador | pass: Demo2026!')
        self.stdout.write('')

    def _vincular_empleado(self):
        """Vincula 'trabajador' al empleado con más datos."""
        try:
            from personal.models import Personal
            from django.db.models import Count

            user = User.objects.get(username='trabajador')

            if hasattr(user, 'personal_data') and user.personal_data:
                anterior = user.personal_data
                if anterior.nro_doc == '47110375':
                    self.stdout.write(
                        f'  [OK] trabajador ya vinculado a: {anterior.apellidos_nombres}'
                    )
                    return
                anterior.usuario = None
                anterior.save()

            empleado = Personal.objects.filter(
                nro_doc='47110375', estado='Activo'
            ).first()

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
                f'(DNI: {empleado.nro_doc})'
            )
        except Exception as e:
            self.stdout.write(f'  [WARN] No se pudo vincular empleado: {e}')

    def _crear_workers_con_dni(self):
        """
        Crea cuentas de portal para todos los Personal que no tienen usuario.
        Username = primera letra del nombre + primer apellido (ej: elopez).
        Password = DNI del trabajador.
        Idempotente.
        """
        try:
            from personal.models import Personal
            import unicodedata

            def _clean(s):
                return ''.join(
                    c for c in unicodedata.normalize('NFD', s.lower())
                    if unicodedata.category(c) != 'Mn'
                ).replace(' ', '')

            def _username(p):
                raw = p.apellidos_nombres.strip()
                if ',' in raw:
                    apellidos_part, nombres_part = raw.split(',', 1)
                    apellido = apellidos_part.strip().split()[0]
                    nombre = nombres_part.strip().split()[0]
                else:
                    tokens = raw.split()
                    apellido = tokens[0] if tokens else ''
                    nombre = tokens[-1] if len(tokens) > 1 else tokens[0]
                base = f'{_clean(nombre)[0]}{_clean(apellido)}'
                username = base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f'{base}{counter}'
                    counter += 1
                    if counter > 99:
                        return p.nro_doc.strip()
                return username

            sin_usuario = Personal.objects.filter(usuario__isnull=True)
            created = 0
            for p in sin_usuario:
                if not p.nro_doc:
                    continue
                try:
                    raw = p.apellidos_nombres.strip()
                    if ',' in raw:
                        last = raw.split(',')[0].strip()
                        first = raw.split(',')[1].strip()
                    else:
                        parts = raw.split()
                        last = ' '.join(parts[:2]) if len(parts) >= 2 else raw
                        first = ' '.join(parts[2:]) if len(parts) > 2 else ''
                    email = getattr(p, 'correo_corporativo', '') or getattr(p, 'correo_personal', '') or ''
                    u = User.objects.create_user(
                        username=_username(p),
                        password=p.nro_doc.strip(),
                        first_name=first[:30],
                        last_name=last[:150],
                        email=email,
                        is_active=True,
                    )
                    p.usuario = u
                    p.save(update_fields=['usuario'])
                    created += 1
                except Exception:
                    pass

            if created:
                self.stdout.write(
                    f'  [OK] {created} cuentas de portal creadas para trabajadores'
                )
        except Exception as e:
            self.stdout.write(f'  [WARN] No se pudieron crear workers: {e}')
