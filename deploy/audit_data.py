import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal, Area, SubArea
from asistencia.models import RegistroTareo, RegistroPapeleta
from nominas.models import PeriodoNomina, RegistroNomina
from vacaciones.models import SolicitudPermiso
from empresas.models import Empresa
from django.db.models import Count, Sum, F, Q
from datetime import date
from decimal import Decimal

print('=' * 70)
print('AUDITORIA COMPLETA DE DATA — HARMONI ERP')
print('=' * 70)

# ── 1. EMPRESA ──
e = Empresa.objects.first()
print(f'\n1. EMPRESA: {e.razon_social} (RUC: {e.ruc})')

# ── 2. PERSONAL ──
print('\n2. PERSONAL')
total = Personal.objects.count()
activos = Personal.objects.filter(estado='Activo').count()
cesados = Personal.objects.filter(estado='Cesado').count()
print(f'   Total: {total} | Activos: {activos} | Cesados: {cesados}')

staff = Personal.objects.filter(estado='Activo', grupo_tareo='STAFF').count()
rco = Personal.objects.filter(estado='Activo', grupo_tareo='RCO').count()
otro_gt = Personal.objects.filter(estado='Activo').exclude(grupo_tareo__in=['STAFF','RCO']).count()
print(f'   STAFF: {staff} | RCO: {rco} | Otro grupo: {otro_gt}')

sin_sueldo = Personal.objects.filter(estado='Activo', sueldo_base=0).count()
sin_area = Personal.objects.filter(estado='Activo', subarea__isnull=True).count()
sin_correo = Personal.objects.filter(estado='Activo', correo_personal='').count()
sin_dni = Personal.objects.filter(estado='Activo', nro_doc='').count()
sin_fecha_alta = Personal.objects.filter(estado='Activo', fecha_alta__isnull=True).count()
sin_fecha_nac = Personal.objects.filter(estado='Activo', fecha_nacimiento__isnull=True).count()
cesados_sin_fecha = Personal.objects.filter(estado='Cesado', fecha_cese__isnull=True).count()
print(f'   ALERTAS:')
print(f'     Sin sueldo: {sin_sueldo}')
print(f'     Sin area: {sin_area}')
print(f'     Sin correo: {sin_correo}')
print(f'     Sin fecha ingreso: {sin_fecha_alta}')
print(f'     Sin fecha nacimiento: {sin_fecha_nac}')
print(f'     Cesados sin fecha cese: {cesados_sin_fecha}')

# Duplicados de DNI
from django.db.models import Count as Cnt
dupes = Personal.objects.values('nro_doc').annotate(c=Cnt('id')).filter(c__gt=1)
if dupes:
    print(f'     DNIs DUPLICADOS: {dupes.count()}')
    for d in dupes:
        print(f'       {d["nro_doc"]}: {d["c"]} registros')

# ── 3. AREAS ──
print(f'\n3. AREAS: {Area.objects.count()} areas, {SubArea.objects.count()} subareas')
areas_vacias = []
for a in Area.objects.all():
    c = Personal.objects.filter(estado='Activo', subarea__area=a).count()
    if c == 0:
        areas_vacias.append(a.nombre)
if areas_vacias:
    print(f'   Areas sin empleados activos: {", ".join(areas_vacias)}')

# ── 4. ASISTENCIA ──
print('\n4. ASISTENCIA (RegistroTareo)')
for m in [1, 2, 3]:
    for g in ['STAFF', 'RCO']:
        c = RegistroTareo.objects.filter(fecha__year=2026, fecha__month=m, grupo=g).count()
        p = RegistroTareo.objects.filter(fecha__year=2026, fecha__month=m, grupo=g).values('personal_id').distinct().count()
        if c:
            print(f'   {g} mes {m}: {c} registros, {p} personas')

# Registros sin personal
sin_personal = RegistroTareo.objects.filter(personal__isnull=True).count()
if sin_personal:
    print(f'   ALERTA: {sin_personal} registros sin personal FK')

# Registros post-cese
post_cese = RegistroTareo.objects.filter(
    personal__fecha_cese__isnull=False,
    fecha__gt=F('personal__fecha_cese')
).count()
print(f'   Registros post-cese: {post_cese}')

# Faltas en domingos LOCAL
dom_fa = RegistroTareo.objects.filter(
    codigo_dia__in=['FA', 'F'],
    condicion__in=['LOCAL', 'LIMA', ''],
    dia_semana=6
).count()
print(f'   FA en domingos LOCAL (deberian ser DS): {dom_fa}')

# Codigos de tareo
print('   Codigos usados:')
codigos = RegistroTareo.objects.values('codigo_dia').annotate(c=Count('id')).order_by('-c')
for c in codigos:
    print(f'     {c["codigo_dia"]}: {c["c"]}')

# ── 5. NOMINAS ──
print('\n5. NOMINAS')
for p in PeriodoNomina.objects.all().order_by('anio', 'mes'):
    regs = RegistroNomina.objects.filter(periodo=p).count()
    print(f'   {p.descripcion}: {regs} registros, bruto=S/{p.total_bruto:,.2f}, neto=S/{p.total_neto:,.2f}')

# Empleados en nomina sin personal
nom_sin = RegistroNomina.objects.filter(personal__isnull=True).count()
if nom_sin:
    print(f'   ALERTA: {nom_sin} registros nomina sin personal')

# ── 6. PAPELETAS ──
print('\n6. PAPELETAS')
total_pap = SolicitudPermiso.objects.count()
print(f'   Total: {total_pap}')
estados = SolicitudPermiso.objects.values('estado').annotate(c=Count('id'))
for e in estados:
    print(f'     {e["estado"]}: {e["c"]}')

pap_sin_personal = RegistroPapeleta.objects.filter(personal__isnull=True).count()
if pap_sin_personal:
    print(f'   ALERTA: {pap_sin_personal} papeletas tareo sin personal')

# ── 7. COHERENCIA CRUZADA ──
print('\n7. COHERENCIA CRUZADA')

# Empleados activos sin asistencia en marzo
activos_ids = set(Personal.objects.filter(estado='Activo').values_list('id', flat=True))
con_tareo_mar = set(RegistroTareo.objects.filter(fecha__year=2026, fecha__month=3).values_list('personal_id', flat=True).distinct())
sin_tareo = activos_ids - con_tareo_mar
print(f'   Activos sin tareo marzo: {len(sin_tareo)}')
if sin_tareo and len(sin_tareo) <= 10:
    for pid in sin_tareo:
        p = Personal.objects.get(id=pid)
        print(f'     {p.nro_doc} {p.apellidos_nombres} (ingreso: {p.fecha_alta})')

# Empleados en nomina enero que no estan en personal
nom_ene_dnis = set()
for rn in RegistroNomina.objects.filter(periodo__mes=1, periodo__anio=2026).select_related('personal'):
    if rn.personal:
        nom_ene_dnis.add(rn.personal.nro_doc)
personal_dnis = set(Personal.objects.values_list('nro_doc', flat=True))
en_nom_no_personal = nom_ene_dnis - personal_dnis
if en_nom_no_personal:
    print(f'   En nomina enero pero no en personal: {len(en_nom_no_personal)}')

# Sueldos: nomina vs personal
print('\n   Comparacion sueldo personal vs nomina enero:')
diffs = 0
for rn in RegistroNomina.objects.filter(periodo__mes=1, periodo__anio=2026).select_related('personal')[:300]:
    if rn.personal and rn.sueldo_base and rn.personal.sueldo_base:
        if abs(rn.sueldo_base - rn.personal.sueldo_base) > 100:
            diffs += 1
print(f'     Diferencias >S/100: {diffs}')

print('\n' + '=' * 70)
print('AUDITORIA COMPLETADA')
print('=' * 70)
