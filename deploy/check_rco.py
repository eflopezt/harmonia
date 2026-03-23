import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from asistencia.models import RegistroTareo
from personal.models import Personal
from datetime import date, timedelta

# Ciclo febrero (21/01 al 20/02)
inicio = date(2026, 1, 21)
fin = date(2026, 2, 20)

# Tomar el primer RCO
rco_pid = RegistroTareo.objects.filter(grupo='RCO', fecha__gte=inicio, fecha__lte=fin, personal__isnull=False).values_list('personal_id', flat=True).first()
p = Personal.objects.get(id=rco_pid)
print(f'Empleado: {p.nro_doc} {p.apellidos_nombres}')
print(f'Ciclo: {inicio} a {fin} ({(fin-inicio).days+1} dias)')

regs = list(RegistroTareo.objects.filter(
    personal=p, grupo='RCO', fecha__gte=inicio, fecha__lte=fin
).order_by('fecha').values('fecha', 'codigo_dia', 'horas_normales', 'he_25', 'he_35', 'he_100'))
print(f'Registros RCO en ciclo: {len(regs)}')

# Ver que dias faltan
fechas_con_reg = {r['fecha'] for r in regs}
d = inicio
while d <= fin:
    has = 'SI' if d in fechas_con_reg else 'NO'
    reg = next((r for r in regs if r['fecha'] == d), None)
    if reg:
        print(f'  {d} {d.strftime("%a")} -> {reg["codigo_dia"]} n={reg["horas_normales"]} h25={reg["he_25"]} h35={reg["he_35"]} h100={reg["he_100"]}')
    else:
        print(f'  {d} {d.strftime("%a")} -> SIN REGISTRO')
    d += timedelta(days=1)

# Ver si tiene registros en otro grupo para esas fechas
staff = RegistroTareo.objects.filter(
    personal=p, grupo='STAFF', fecha__gte=inicio, fecha__lte=fin
).count()
print(f'\nRegistros STAFF mismo periodo: {staff}')

# Ahora probar el build
from asistencia.views.reporte_individual import _build_rco_data, _get_ciclo
inicio2, fin2 = _get_ciclo(2026, 2)
print(f'\n_get_ciclo(2026,2) = {inicio2} a {fin2}')
dias, totales = _build_rco_data(p, inicio2, fin2)
print(f'_build_rco_data: {len(dias)} dias')
dias_con_codigo = [d for d in dias if d['codigo']]
print(f'  Con codigo: {len(dias_con_codigo)}')
print(f'  Sin codigo: {len(dias) - len(dias_con_codigo)}')
print(f'  Totales: {totales}')
