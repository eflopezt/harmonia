import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal
from datetime import date

p = Personal.objects.get(nro_doc='75926982')
print(f'{p.apellidos_nombres}')
print(f'cese={p.fecha_cese}')

# Ciclo marzo: 21/02 al 20/03
inicio = date(2026, 2, 21)
fin = date(2026, 3, 20)
print(f'\nCiclo marzo (planilla): {inicio} al {fin}')

regs = RegistroTareo.objects.filter(personal=p, fecha__gte=inicio, fecha__lte=fin).order_by('fecha')
print(f'Registros en ciclo: {regs.count()}')
for r in regs:
    dow = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'][r.fecha.weekday()]
    dentro = 'OK' if r.fecha <= p.fecha_cese else 'POST-CESE'
    print(f"  {r.fecha} {dow}: {r.codigo_dia} [{dentro}]")

# Vista STAFF filtra por mes calendario
mes_ini = date(2026, 3, 1)
mes_fin = date(2026, 3, 31)
regs_mes = RegistroTareo.objects.filter(personal=p, fecha__gte=mes_ini, fecha__lte=mes_fin)
print(f'\nRegistros mes calendario marzo: {regs_mes.count()}')

# Febrero
feb_regs = RegistroTareo.objects.filter(personal=p, fecha__year=2026, fecha__month=2).order_by('fecha')
print(f'\nRegistros febrero: {feb_regs.count()}')
for r in feb_regs.filter(fecha__gte=date(2026,2,21)):
    dow = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'][r.fecha.weekday()]
    print(f"  {r.fecha} {dow}: {r.codigo_dia}")
