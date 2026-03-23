import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from personal.models import Personal
print(f'Activos: {Personal.objects.filter(estado="Activo").count()}')
print(f'Cesados: {Personal.objects.filter(estado="Cesado").count()}')
print(f'Total: {Personal.objects.count()}')
