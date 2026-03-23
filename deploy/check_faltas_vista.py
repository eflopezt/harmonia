import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal
from django.db.models import Count, F

print('=== Vista STAFF marzo - analisis de faltas ===')

# La vista STAFF usa _qs_staff_dedup que NO excluye domingos ni cesados
# El filtro de faltas se hace en el TEMPLATE con el conteo de dias_fa
# Verificar: la vista staff.py line 72: dias_fa = Count('id', filter=Q(codigo_dia__in=['FA', 'F']))
# Este conteo NO excluye domingos LOCAL ni post-cese

# Cuantos FA hay en STAFF marzo
from asistencia.views._common import _qs_staff_dedup
from datetime import date
mes_ini = date(2026, 3, 1)
mes_fin = date(2026, 3, 31)

qs = _qs_staff_dedup(mes_ini, mes_fin)
total = qs.count()
fa_total = qs.filter(codigo_dia__in=['FA', 'F']).count()
fa_dom_local = qs.filter(codigo_dia__in=['FA', 'F'], condicion__in=['LOCAL', 'LIMA', ''], dia_semana=6).count()
fa_post_cese = qs.filter(codigo_dia__in=['FA', 'F'], personal__fecha_cese__isnull=False, fecha__gt=F('personal__fecha_cese')).count()

print(f'Total registros STAFF marzo: {total}')
print(f'FA total: {fa_total}')
print(f'FA domingos LOCAL: {fa_dom_local}')
print(f'FA post-cese: {fa_post_cese}')
print(f'FA reales: {fa_total - fa_dom_local - fa_post_cese}')

# La vista staff.py NO aplica estos filtros - es el problema
print('\n=== El problema: staff.py NO excluye domingos LOCAL ni post-cese en dias_fa ===')
