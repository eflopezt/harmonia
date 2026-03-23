import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup()
from personal.models import Personal
from asistencia.models import RegistroTareo
from asistencia.views.reporte_individual import _build_rco_data, _auto_ds, _get_ciclo

inicio, fin = _get_ciclo(2026, 3)

for dni in ['46127028', '73451822', '43290334']:
    p = Personal.objects.get(nro_doc=dni)
    dias, tot = _build_rco_data(p, inicio, fin)
    print(f'\n{dni} {p.apellidos_nombres} condicion={p.condicion}')
    domingos = [d for d in dias if d['fecha'].weekday() == 6]
    for d in domingos:
        fecha = d['fecha']
        # Ver raw data
        raw = list(RegistroTareo.objects.filter(personal=p, fecha=fecha).values('grupo','codigo_dia'))
        print(f"  {fecha} Dom: build_result={d['codigo']}  raw={raw}")
        # Test _auto_ds
        for r in raw:
            auto = _auto_ds(fecha, r['codigo_dia'], p.condicion)
            print(f"    _auto_ds('{r['codigo_dia']}', '{p.condicion}') = '{auto}'")
