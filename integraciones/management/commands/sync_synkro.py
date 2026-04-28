"""
Comando: sincronización directa con la BD remota de Synkro RRHH.

Uso:
    python manage.py sync_synkro
    python manage.py sync_synkro --ventana-dias 90
    python manage.py sync_synkro --reset-cursor    # ignora último cursor
    python manage.py sync_synkro --dry-run          # solo reporta, no escribe
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sincroniza papeletas, picados y feriados desde Synkro RRHH.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ventana-dias', type=int, default=60,
            help='Días hacia atrás para procesar picados (default: 60).',
        )
        parser.add_argument(
            '--reset-cursor', action='store_true',
            help='Ignora el cursor de la última corrida y reprocesa.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo verifica conexión y reporta, no modifica datos.',
        )

    def handle(self, *args, **opts):
        from integraciones.services.synkro_sync import run_sync
        from integraciones.synkro_models import PicadoPersonal

        if opts['dry_run']:
            # Test de conexión + conteo
            from django.db import connections
            try:
                conn = connections['synkro']
                conn.ensure_connection()
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Conexión synkro OK ({conn.settings_dict.get("HOST")})'
                ))
                total = PicadoPersonal.objects.using('synkro').count()
                self.stdout.write(f'Total picados en Synkro: {total:,}')
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'✗ Error: {exc}'))
            return

        if opts['reset_cursor']:
            from integraciones.models import SyncSynkroLog
            SyncSynkroLog.objects.filter(estado='OK').update(
                cursor_papeletas=None, cursor_picados=None,
            )
            self.stdout.write(self.style.WARNING('Cursores reseteados.'))

        log = run_sync(origen='CLI', ventana_picados_dias=opts['ventana_dias'])

        self.stdout.write('')
        self.stdout.write(f'Estado: {log.estado}  |  Duración: {log.duracion_segundos}s')
        self.stdout.write(f'  Feriados creados:        {log.feriados_creados}')
        self.stdout.write(f'  Papeletas creadas:       {log.papeletas_creadas}')
        self.stdout.write(f'  Papeletas actualizadas:  {log.papeletas_actualizadas}')
        self.stdout.write(f'  Papeletas omitidas:      {log.papeletas_omitidas}')
        self.stdout.write(f'  RegistroTareo creados:   {log.registros_tareo_creados}')
        self.stdout.write(f'  RegistroTareo actualiz.: {log.registros_tareo_actualizados}')
        self.stdout.write(f'  Personas no encontradas: {log.personas_no_encontradas}')
        if log.estado == 'ERROR':
            self.stdout.write(self.style.ERROR(f'\nError: {log.error_mensaje}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Sync completado.'))
