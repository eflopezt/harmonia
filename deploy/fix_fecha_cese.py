import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from personal.models import Personal
from asistencia.models import RegistroTareo
from django.db.models import Max

# Cesados sin fecha_cese
sin_fecha = Personal.objects.filter(estado='Cesado', fecha_cese__isnull=True)
print(f'Cesados sin fecha_cese: {sin_fecha.count()}')

for p in sin_fecha:
    # Usar fecha_fin_contrato si existe
    if p.fecha_fin_contrato:
        p.fecha_cese = p.fecha_fin_contrato
        p.save(update_fields=['fecha_cese'])
        print(f'  {p.nro_doc} {p.apellidos_nombres}: cese={p.fecha_fin_contrato} (de contrato)')
        continue

    # Si no, usar la última fecha de tareo
    ultimo = RegistroTareo.objects.filter(personal=p).aggregate(max_f=Max('fecha'))
    if ultimo['max_f']:
        p.fecha_cese = ultimo['max_f']
        p.save(update_fields=['fecha_cese'])
        print(f'  {p.nro_doc} {p.apellidos_nombres}: cese={ultimo["max_f"]} (ultimo tareo)')
    else:
        # Sin tareo, usar hoy
        from datetime import date
        p.fecha_cese = date.today()
        p.save(update_fields=['fecha_cese'])
        print(f'  {p.nro_doc} {p.apellidos_nombres}: cese={date.today()} (sin tareo, usando hoy)')

# Verificar
sin = Personal.objects.filter(estado='Cesado', fecha_cese__isnull=True).count()
print(f'\nCesados sin fecha_cese despues del fix: {sin}')
