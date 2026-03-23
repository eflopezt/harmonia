import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from personal.models import Personal
from django.db.models import F, Count

print('=== Registros FUERA de periodo laboral ===\n')

# Pre-ingreso
pre = RegistroTareo.objects.filter(
    personal__fecha_alta__isnull=False,
    fecha__lt=F('personal__fecha_alta')
)
print(f'Pre-ingreso (fecha < fecha_alta): {pre.count()} registros')
afectados_pre = pre.values('personal__nro_doc', 'personal__apellidos_nombres', 'personal__fecha_alta').annotate(c=Count('id')).order_by('-c')
for a in afectados_pre[:10]:
    print(f"  {a['personal__nro_doc']} {a['personal__apellidos_nombres']}: {a['c']} registros antes de {a['personal__fecha_alta']}")
if afectados_pre.count() > 10:
    print(f'  ... y {afectados_pre.count() - 10} mas')

# Post-cese
post = RegistroTareo.objects.filter(
    personal__fecha_cese__isnull=False,
    fecha__gt=F('personal__fecha_cese')
)
print(f'\nPost-cese (fecha > fecha_cese): {post.count()} registros')
afectados_post = post.values('personal__nro_doc', 'personal__apellidos_nombres', 'personal__fecha_cese').annotate(c=Count('id')).order_by('-c')
for a in afectados_post[:10]:
    print(f"  {a['personal__nro_doc']} {a['personal__apellidos_nombres']}: {a['c']} registros despues de {a['personal__fecha_cese']}")
if afectados_post.count() > 10:
    print(f'  ... y {afectados_post.count() - 10} mas')

print(f'\nTOTAL registros fantasma: {pre.count() + post.count()}')
print(f'Estos ya se EXCLUYEN de vistas, dashboards, KPIs y reportes PDF')
