"""
fix_areas_duplicadas.py
Fusiona áreas duplicadas (mismo nombre, distinto formato de capitalización/tildes).
Ejecutar: python fix_areas_duplicadas.py
"""
import os, sys, unicodedata
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
sys.path.insert(0, 'D:/Harmoni')
import django
django.setup()

from collections import defaultdict
from personal.models import Area, SubArea, Personal


def norm(s):
    """'Administración' -> 'ADMINISTRACION' (sin tildes, mayúsculas)"""
    s = s.strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


# ── 1. Encontrar grupos duplicados ──────────────────────────────────────────
grupos = defaultdict(list)
for a in Area.objects.all().order_by('id'):
    grupos[norm(a.nombre)].append(a)

duplicados = {k: v for k, v in grupos.items() if len(v) > 1}
print(f"Grupos con duplicados: {len(duplicados)}")

if not duplicados:
    print("No hay duplicados. Nada que hacer.")
    sys.exit(0)

# ── 2. Fusionar ─────────────────────────────────────────────────────────────
total_eliminadas = 0
for nombre_norm, areas in duplicados.items():
    # Elegir canónica: prioridad (1) tiene código, (2) más subareas, (3) menor id
    areas.sort(key=lambda a: (
        0 if a.codigo else 1,
        -SubArea.objects.filter(area=a).count(),
        a.id
    ))
    canonica = areas[0]
    duplicadas = areas[1:]

    n_emp = Personal.objects.filter(subarea__area=canonica).count()
    print(f"\n[{nombre_norm}] Principal: '{canonica.nombre}' (id={canonica.id}, "
          f"code='{canonica.codigo}', emp={n_emp})")

    for dup in duplicadas:
        print(f"  Fusionando '{dup.nombre}' (id={dup.id})...")

        for sub in SubArea.objects.filter(area=dup):
            # Buscar subarea equivalente en la canónica
            matching = SubArea.objects.filter(area=canonica, nombre=sub.nombre).first()
            if matching:
                moved = Personal.objects.filter(subarea=sub).update(subarea=matching)
                print(f"    SubArea '{sub.nombre}': {moved} empleados -> subarea existente")
                sub.delete()
            else:
                sub.area = canonica
                sub.save()
                print(f"    SubArea '{sub.nombre}': reasignada a principal")

        dup.delete()
        print(f"    Area '{dup.nombre}' eliminada.")
        total_eliminadas += 1

# ── 3. Normalizar nombres de áreas restantes ─────────────────────────────────
print("\n-- Normalizando nombres de areas --")
import re

def titulo_es(s):
    """'ADMINISTRACION' -> 'Administración' usando mapa de acentos"""
    ACENTOS = {
        'ADMINISTRACION': 'Administración',
        'GERENCIA': 'Gerencia',
        'FINANZAS': 'Finanzas',
        'LOGISTICA': 'Logística',
        'INFORMATICA': 'Informática',
        'PRODUCCION': 'Producción',
        'OPERACIONES': 'Operaciones',
        'RECURSOS HUMANOS': 'Recursos Humanos',
        'CONTABILIDAD': 'Contabilidad',
        'LEGAL': 'Legal',
        'COMERCIAL': 'Comercial',
        'SEGURIDAD': 'Seguridad',
    }
    n = norm(s)
    return ACENTOS.get(n, s.title())

actualizadas = 0
for area in Area.objects.all():
    nombre_correcto = titulo_es(area.nombre)
    if area.nombre != nombre_correcto:
        print(f"  '{area.nombre}' -> '{nombre_correcto}'")
        area.nombre = nombre_correcto
        area.save()
        actualizadas += 1

print(f"\nRESUMEN:")
print(f"  Areas eliminadas (duplicados):  {total_eliminadas}")
print(f"  Areas renombradas (formato):     {actualizadas}")
print(f"  Areas totales restantes:         {Area.objects.count()}")
print(f"  SubAreas totales:                {SubArea.objects.count()}")
