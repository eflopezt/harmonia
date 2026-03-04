"""
Management command: sync_relojes

Sincroniza todos los relojes biométricos activos (o uno específico)
descargando marcaciones desde los dispositivos ZKTeco via protocolo ZK.

Uso:
    # Sincronizar todos los relojes activos
    python manage.py sync_relojes

    # Sincronizar un reloj específico por ID
    python manage.py sync_relojes --reloj 3

    # Solo probar conexiones sin guardar marcaciones (dry-run)
    python manage.py sync_relojes --dry-run

    # Procesar marcaciones a RegistroTareo después de la sync
    python manage.py sync_relojes --procesar --fecha-ini 2026-03-01 --fecha-fin 2026-03-31

Ideal para ejecutar desde cron / Celery Beat:
    0 7 * * 1-6  python manage.py sync_relojes  # Lunes-Sábado a las 7:00 AM
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Sincroniza marcaciones desde relojes biométricos ZKTeco.'

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

    def handle(self, *args: Any, **options: Any):
        from asistencia.models import RelojBiometrico
        from asistencia.services.zk_service import ZKService

        # ── Verificar pyzk ────────────────────────────────────────────
        try:
            import zk  # noqa
        except ImportError:
            raise CommandError(
                'pyzk no está instalado. Ejecuta: pip install pyzk'
            )

        dry_run  = options['dry_run']
        procesar = options['procesar']

        # ── Obtener relojes a sincronizar ─────────────────────────────
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
                f'  Harmoni — Sincronización ZKTeco\n'
                f'  {total_relojes} reloj(es) {"(DRY-RUN)" if dry_run else ""}\n'
                f'{"=" * 60}\n'
            )
        )

        # ── Sincronizar cada reloj ────────────────────────────────────
        user = User.objects.filter(is_superuser=True).first()
        total_nuevos = total_omitidos = total_sin_match = 0

        for reloj in relojes:
            self.stdout.write(f'\n▶ {reloj.nombre} ({reloj.ip}:{reloj.puerto})')

            svc = ZKService(reloj)

            if dry_run:
                result = svc.test_connection()
                if result['ok']:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Conectado — {result["detail"]}')
                    )
                    info = result.get('info', {})
                    if info.get('serial'):
                        self.stdout.write(f'    Serie: {info["serial"]}')
                    if info.get('firmware'):
                        self.stdout.write(f'    Firmware: {info["firmware"]}')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error — {result["detail"]}')
                    )
                continue

            # Pull attendance
            self.stdout.write('  Descargando marcaciones…')
            result = svc.pull_attendance(user=user)

            if result['ok']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Total: {result["total"]} | '
                        f'Nuevas: {result["nuevos"]} | '
                        f'Duplicadas: {result["omitidos"]} | '
                        f'Sin match DNI: {result["sin_match"]}'
                    )
                )
                total_nuevos    += result['nuevos']
                total_omitidos  += result['omitidos']
                total_sin_match += result['sin_match']
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {result["error"]}')
                )

        # ── Procesar a RegistroTareo ──────────────────────────────────
        if procesar and not dry_run:
            self.stdout.write(self.style.HTTP_INFO('\n── Procesando marcaciones a RegistroTareo…'))

            # Fechas del período
            if options['fecha_ini'] and options['fecha_fin']:
                try:
                    fecha_ini = date.fromisoformat(options['fecha_ini'])
                    fecha_fin = date.fromisoformat(options['fecha_fin'])
                except ValueError as e:
                    raise CommandError(f'Fecha inválida: {e}')
            else:
                hoy = date.today()
                fecha_ini = hoy.replace(day=1)
                fecha_fin = hoy
                self.stdout.write(
                    self.style.WARNING(
                        f'  Fechas no especificadas. Usando mes actual: '
                        f'{fecha_ini} → {fecha_fin}'
                    )
                )

            for reloj in relojes:
                svc = ZKService(reloj)
                self.stdout.write(f'\n  ▶ Procesando: {reloj.nombre}')
                result = svc.procesar_a_tareo(fecha_ini, fecha_fin, user=user)

                if result['ok']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Importación #{result["importacion_id"]} | '
                            f'Creados: {result["creados"]} | '
                            f'Actualizados: {result["actualizados"]} | '
                            f'Sin match: {result["sin_match"]}'
                        )
                    )
                    if result.get('errores'):
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠ {len(result["errores"])} errores al procesar'
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error al procesar: {result["error"]}')
                    )

        # ── Resumen final ─────────────────────────────────────────────
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n{"=" * 60}\n'
                    f'  ✓ Sync completada\n'
                    f'  Nuevas marcaciones: {total_nuevos}\n'
                    f'  Duplicadas (omitidas): {total_omitidos}\n'
                    f'  Sin match DNI: {total_sin_match}\n'
                    f'{"=" * 60}\n'
                )
            )
