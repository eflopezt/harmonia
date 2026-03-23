import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from datetime import datetime
from personal.models import Personal

with open('/app/cesados_actualizar.json', encoding='utf-8') as f:
    cesados = json.load(f)

MOTIVO_MAP = {
    'TERMINO DE CONTRATO': 'VENCIMIENTO',
    'RENUNCIA VOLUNTARIA': 'RENUNCIA',
    'RENUNCIA': 'RENUNCIA',
    'MUTUO ACUERDO': 'MUTUO_ACUERDO',
    'DESPIDO': 'DESPIDO_CAUSA',
}

actualizados = 0
ya_cesados = 0
no_encontrados = 0

for c in cesados:
    dni = c['dni'].strip()
    fecha_cese = datetime.strptime(c['fecha_cese'], '%Y-%m-%d').date()
    motivo_raw = c.get('motivo', 'TERMINO DE CONTRATO').strip().upper()
    motivo = MOTIVO_MAP.get(motivo_raw, 'VENCIMIENTO')

    p = Personal.objects.filter(nro_doc=dni).first()
    if not p:
        p = Personal.objects.filter(nro_doc=dni.lstrip('0')).first()
    if not p:
        p = Personal.objects.filter(nro_doc=dni.zfill(8)).first()

    if not p:
        no_encontrados += 1
        print(f'  NO ENCONTRADO: {dni} {c.get("nombre", "")}')
        continue

    changed = False
    if p.estado != 'Cesado':
        p.estado = 'Cesado'
        changed = True
    if p.fecha_cese != fecha_cese:
        p.fecha_cese = fecha_cese
        changed = True
    if p.motivo_cese != motivo:
        p.motivo_cese = motivo
        changed = True

    if changed:
        p.save()
        actualizados += 1
        print(f'  ACTUALIZADO: {dni} {p.apellidos_nombres} -> cese={fecha_cese} motivo={motivo}')
    else:
        ya_cesados += 1

print(f'\nResultado:')
print(f'  Actualizados: {actualizados}')
print(f'  Ya estaban OK: {ya_cesados}')
print(f'  No encontrados: {no_encontrados}')
print(f'  Activos: {Personal.objects.filter(estado="Activo").count()}')
print(f'  Cesados: {Personal.objects.filter(estado="Cesado").count()}')
