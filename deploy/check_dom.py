import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from asistencia.models import RegistroTareo
from datetime import date

domingos = [date(2026,2,22), date(2026,3,1), date(2026,3,8), date(2026,3,15)]
for dom in domingos:
    regs = list(RegistroTareo.objects.filter(personal__nro_doc='43290334', fecha=dom).values('grupo','codigo_dia'))
    if regs:
        for r in regs:
            print(f"  {dom} (Dom): grupo={r['grupo']} codigo={r['codigo_dia']}")
    else:
        print(f"  {dom} (Dom): SIN REGISTRO")
