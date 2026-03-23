import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal

with open('/app/correos.json', encoding='utf-8') as f:
    correos = json.load(f)

updated = 0
for p in Personal.objects.all():
    email = correos.get(p.nro_doc) or correos.get(p.nro_doc.lstrip('0'))
    if not email:
        continue
    if p.correo_personal != email:
        p.correo_personal = email
        p.save(update_fields=['correo_personal'])
        updated += 1

sin_correo = Personal.objects.filter(estado='Activo', correo_personal='').count()
con_correo = Personal.objects.filter(estado='Activo').exclude(correo_personal='').count()
total = Personal.objects.filter(estado='Activo').count()
print(f'Actualizados: {updated}')
print(f'Activos con correo: {con_correo}/{total}')
print(f'Activos sin correo: {sin_correo}')
