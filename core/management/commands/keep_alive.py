"""
keep_alive.py — Pinga el endpoint /health/ para mantener Render despierto.
Uso: python manage.py keep_alive
Configurable via env: SITE_URL (default: https://harmoni.pe)
"""
import time
import urllib.request
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Pinga /health/ periódicamente para evitar sleep en Render free tier'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=600,
                            help='Segundos entre pings (default: 600 = 10min)')

    def handle(self, *args, **options):
        url = os.environ.get('SITE_URL', 'https://harmoni.pe').rstrip('/') + '/health/'
        interval = options['interval']
        self.stdout.write(f'Keep-alive activo: {url} cada {interval}s')
        while True:
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    self.stdout.write(f'  ping OK ({r.status})')
            except Exception as e:
                self.stdout.write(f'  ping FAIL: {e}')
            time.sleep(interval)
