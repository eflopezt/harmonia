"""
Management command: sync_biometricos

Sincroniza todos los relojes biométricos activos (o uno específico)
descargando marcaciones desde dispositivos ZKTeco via protocolo ZK.

Usa la nueva clase ZKTecoService para la comunicación directa.

Uso:
    # Sincronizar todos los relojes activos
    python manage.py sync_biometricos

    # Sincronizar un reloj específico por ID
    python manage.py sync_biometricos --reloj 3

    # Solo probar conexiones sin guardar marcaciones (dry-run)
    python manage.py sync_biometricos --dry-run

    # Sincronizar y procesar marcaciones a RegistroTareo
    python manage.py sync_biometricos --procesar --fecha-ini 2026-03-01 --fecha-fin 2026-03-31

    # Subir empleados al dispositivo
    python manage.py sync_biometricos --reloj 3 --upload-users

Ideal para ejecutar desde cron / Celery Beat:
    */15 * * * *  python manage.py sync_biometricos  # Cada 15 minutos
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('harmoni.zkteco')


class Command(BaseCommand):
    help = 'Sincroniza marcaciones desde relojes biométricos ZKTeco usando ZKTecoService.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reloj', type=int, default=None,
            metavar='ID',
            help='ID del RelojBiometrico a sincronizar (por defecto: todos los activos)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo prueba la conexión, no guarda marcaciones.',
        )
        parser.add_argument(
            '--procesar', action='store_true',
            help='Después de sincronizar, procesa marcaciones a RegistroTareo.',
        )
        parser.add_argument(
            '--fecha-ini', type=str, default=None,
            metavar='YYYY-MM-DD',
            help='Inicio del período a procesar (requiere --procesar).',
        )
        parser.add_argument(
            '--fecha-fin', type=str, default=None,
            metavar='YYYY-MM-DD',
            help='Fin del período a procesar (requiere --procesar).',
        )
        parser.add_argument(
            '--upload-users', action='store_true',
            help='Sube empleados activos al dispositivo (requiere --reloj).',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Limpia las marcaciones del dispositivo después de sincronizar.',
        )

    def handle(self, *args: Any, **options: Any):
        from asistencia.models import RelojBiometrico
        from asistencia.services.zkteco_service import ZKTecoService, sync_device_attendance

        # Verify pyzk
        try:
            import zk  # noqa
        except ImportError:
            raise CommandError(
                'pyzk no está instalado. Ejecuta: pip install pyzk'
            )

        dry_run = options['dry_run']
        procesar = options['procesar']
        upload_users = options['upload_users']
        clear_after = options['clear']

        # Get devices
        if options['reloj']:
            relojes = RelojBiometrico.objects.filter(pk=options['reloj'])
            if not relojes.exists():
                raise CommandError(f"RelojBiometrico ID {options['reloj']} no encontrado.")
        else:
            relojes = RelojBiometrico.objects.filter(activo=True)

        total_relojes = relojes.count()
        if total_relojes == 0:
            self.stdout.write(self.style.WARNING('No hay relojes activos configurados.'))
            return

        self.stdout.write(
            self.style.HTTP_INFO(
                f'\n{"=" * 60}\n'
                f'  Harmoni - Sincronizacion ZKTeco (ZKTecoService)\n'
                f'  {total_relojes} reloj(es) {"(DRY-RUN)" if dry_run else ""}\n'
                f'{"=" * 60}\n'
            )
        )

        user = User.objects.filter(is_superuser=True).first()
        total_nuevos = total_omitidos = total_sin_match = 0

        for reloj in relojes:
            self.stdout.write(f'\n>> {reloj.nombre} ({reloj.ip}:{reloj.puerto})')

            if dry_run:
                svc = ZKTecoService()
                result = svc.test_connection(reloj.ip, reloj.puerto)
                if result['ok']:
                    self.stdout.write(
                        self.style.SUCCESS(f'  OK - {result["detail"]}')
                    )
                    info = result.get('info', {})
                    if info.get('serial'):
                        self.stdout.write(f'    Serie: {info["serial"]}')
                    if info.get('firmware'):
                        self.stdout.write(f'    Firmware: {info["firmware"]}')
                    if info.get('user_count'):
                        self.stdout.write(f'    Usuarios: {info["user_count"]}')
                    if info.get('attendance_count'):
                        self.stdout.write(f'    Marcaciones en dispositivo: {info["attendance_count"]}')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  FALLO - {result["detail"]}')
                    )
                continue

            # Upload users if requested
            if upload_users:
                self._upload_users(reloj)
                continue

            # Sync attendance
            self.stdout.write('  Descargando marcaciones...')
            result = sync_device_attendance(reloj, user=user)

            if result['ok']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  OK Total: {result["total"]} | '
                        f'Nuevas: {result["nuevos"]} | '
                        f'Duplicadas: {result["omitidos"]} | '
                        f'Sin match DNI: {result["sin_match"]}'
                    )
                )
                total_nuevos += result['nuevos']
                total_omitidos += result['omitidos']
                total_sin_match += result['sin_match']

                # Clear device attendance if requested
                if clear_after and result['nuevos'] > 0:
                    self._clear_device(reloj)
            else:
                self.stdout.write(
                    self.style.ERROR(f'  FALLO: {result["error"]}')
                )

        # Process to RegistroTareo
        if procesar and not dry_run and not upload_users:
            self._procesar_tareo(relojes, options, user)

        # Final summary
        if not dry_run and not upload_users:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n{"=" * 60}\n'
                    f'  Sync completada\n'
                    f'  Nuevas marcaciones: {total_nuevos}\n'
                    f'  Duplicadas (omitidas): {total_omitidos}\n'
                    f'  Sin match DNI: {total_sin_match}\n'
                    f'{"=" * 60}\n'
                )
            )

    def _upload_users(self, reloj):
        """Upload active employees to a device."""
        from asistencia.services.zkteco_service import ZKTecoService
        from personal.models import Personal

        employees = Personal.objects.filter(
            activo=True,
        ).values('nro_doc', 'apellidos_nombres')

        if not employees:
            self.stdout.write(self.style.WARNING('  No hay empleados activos.'))
            return

        emp_list = [
            {
                'user_id': e['nro_doc'],
                'name': (e['apellidos_nombres'] or '')[:24],
            }
            for e in employees if e['nro_doc']
        ]

        svc = ZKTecoService()
        try:
            svc.connect(reloj.ip, port=reloj.puerto, timeout=reloj.timeout)
            result = svc.sync_users(emp_list)
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Usuarios subidos: {result["uploaded"]} | '
                    f'Ya existian: {result["skipped"]} | '
                    f'Errores: {result["errors"]}'
                )
            )
            if result['details']:
                for d in result['details'][:10]:
                    self.stdout.write(self.style.WARNING(f'    {d}'))
        except (ImportError, ConnectionError) as exc:
            self.stdout.write(self.style.ERROR(f'  Error: {exc}'))
        finally:
            svc.disconnect()

    def _clear_device(self, reloj):
        """Clear attendance records from the device."""
        from asistencia.services.zkteco_service import ZKTecoService

        svc = ZKTecoService()
        try:
            svc.connect(reloj.ip, port=reloj.puerto, timeout=reloj.timeout)
            svc.clear_attendance()
            self.stdout.write(self.style.SUCCESS('  Marcaciones del dispositivo limpiadas.'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  Error al limpiar: {exc}'))
        finally:
            svc.disconnect()

    def _procesar_tareo(self, relojes, options, user):
        """Process downloaded attendance into RegistroTareo."""
        from asistencia.services.zk_service import ZKService

        self.stdout.write(self.style.HTTP_INFO('\n-- Procesando marcaciones a RegistroTareo...'))

        if options['fecha_ini'] and options['fecha_fin']:
            try:
                fecha_ini = date.fromisoformat(options['fecha_ini'])
                fecha_fin = date.fromisoformat(options['fecha_fin'])
            except ValueError as e:
                self.stdout.write(self.style.ERROR(f'Fecha invalida: {e}'))
                return
        else:
            hoy = date.today()
            fecha_ini = hoy.replace(day=1)
            fecha_fin = hoy
            self.stdout.write(
                self.style.WARNING(
                    f'  Fechas no especificadas. Usando mes actual: '
                    f'{fecha_ini} -> {fecha_fin}'
                )
            )

        for reloj in relojes:
            svc = ZKService(reloj)
            self.stdout.write(f'\n  >> Procesando: {reloj.nombre}')
            result = svc.procesar_a_tareo(fecha_ini, fecha_fin, user=user)

            if result['ok']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  OK Importacion #{result["importacion_id"]} | '
                        f'Creados: {result["creados"]} | '
                        f'Actualizados: {result["actualizados"]} | '
                        f'Sin match: {result["sin_match"]}'
                    )
                )
                if result.get('errores'):
                    self.stdout.write(
                        self.style.WARNING(
                            f'  {len(result["errores"])} errores al procesar'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'  Error al procesar: {result["error"]}')
                )
