import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from personal.models import Personal

cesados = Personal.objects.filter(estado='Cesado').order_by('-fecha_cese')
print(f'Cesados: {cesados.count()}')
print(f'\nCon fecha_cese:')
for p in cesados:
    fc = p.fecha_cese.strftime('%d/%m/%Y') if p.fecha_cese else 'SIN FECHA!'
    print(f'  {p.nro_doc} {p.apellidos_nombres}: cese={fc} motivo={p.motivo_cese}')

sin_fecha = cesados.filter(fecha_cese__isnull=True)
print(f'\nCesados SIN fecha_cese: {sin_fecha.count()}')
for p in sin_fecha:
    print(f'  {p.nro_doc} {p.apellidos_nombres}')
