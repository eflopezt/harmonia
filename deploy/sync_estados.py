"""Sincronizar estados de empleados con lista real de activos."""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal

# DNIs que DEBEN ser activos (lista del usuario)
ACTIVOS_REALES = {
    '23981390','75337871','78286420','70614124','43382768','40548472','41670147',
    '40308469','08851995','70415206','43495610','001993770','41531855','42791076',
    '72428140','70570380','43454812','47964954','72217746','31189140','47773807',
    '73147728','47330689','77127124','42390562','44616975','44261132','41248182',
    '45917823','74144528','001526140','73932761','45231234','46686215','72573615',
    '48000903','77296315','71589955','41598491','32136077','71334912','77059328',
    '74539175','73194963','72020477','43935996','43600466','46840428','48028346',
    '72459185','72257483','47605746','10105707','45857954','43156036','43801267',
    '72901854','70574711','47110375','48037224','71574176','70887797','48091922',
    '005835751','005892606','007453650','005419022','43738113','73481466','48056430',
    '74925154','76675994','76801259','72166636','70829013','73445337','60117582',
    '73014549','03689683','47069792','44666461','41818325','21261940','74076597',
    '45796382','70786569','72129488','75940400','46877005','47832664','70495252',
    '21811280','73990329','75810956','46275287','46734880','76306720','47583164',
    '76755635','73301144','75196505','10515850','75682513','45656788','10714475',
    '74716792','72750116','74471124','75314991','76807186','76587790','24995251',
    '76543124','70830057','73965216','73111816','45676771','72539322','42319767',
    '73352896','73962431','71706552','60019040','75581956','70462078','70275978',
    '74657049','47987309','73202371','76278558','70393462','71075941','62140146',
    '74784658','48177998','45311345','76834291','73197310','46127028','72553778',
    '72942596','70337517','24007726','46750155','73451822','78006445','72782212',
    '70079643','72268347','74634862','72440813','70024630','73644767','41296195',
    '70784205','45275146','77904197','71414045','16790781','43567961','72686304',
    '43290334','70919188','45507761','73086057','23925262','73823718','74465253',
    '73813950','40139383','10216742','08158055','77028590','73185758','76924783',
    '71483927','72261810','72269533','40741044','72299026','76881990','72582627',
    '74161026','71466578','72653934','42034955','71798550','72634497','70939038',
    '70001603','70482474','29685086','74065363',
    # Cesados según la lista
    # '71405212' -> cesado 4/03/2026
    # '73745968' -> cesado 7/03/2026
    # '73012587' -> cesado 15/03/2026
}

# Normalizar: agregar variantes sin ceros y con ceros
activos_norm = set()
for d in ACTIVOS_REALES:
    activos_norm.add(d)
    activos_norm.add(d.lstrip('0'))
    if len(d) < 8:
        activos_norm.add(d.zfill(8))
        activos_norm.add(d.zfill(9))

# Empleados que deben ser cesados según la lista
CESADOS_LISTA = {
    '71405212': '2026-03-04',
    '73745968': '2026-03-07',
    '73012587': '2026-03-15',
}

corregidos_cesado = 0
corregidos_activo = 0

for p in Personal.objects.all():
    dni = p.nro_doc
    dni_clean = dni.lstrip('0')

    # Verificar si está en lista de cesados explícitos
    if dni in CESADOS_LISTA or dni_clean in CESADOS_LISTA:
        if p.estado != 'Cesado':
            fecha_cese_str = CESADOS_LISTA.get(dni, CESADOS_LISTA.get(dni_clean))
            from datetime import datetime
            p.estado = 'Cesado'
            p.fecha_cese = datetime.strptime(fecha_cese_str, '%Y-%m-%d').date()
            p.motivo_cese = 'TERMINO DE CONTRATO'
            p.save()
            corregidos_cesado += 1
            print(f'  CESADO: {dni} {p.apellidos_nombres} -> cese {fecha_cese_str}')
        continue

    # Si está en la lista de activos reales
    if dni in activos_norm or dni_clean in activos_norm:
        if p.estado != 'Activo':
            p.estado = 'Activo'
            p.fecha_cese = None
            p.save()
            corregidos_activo += 1
            print(f'  ACTIVADO: {dni} {p.apellidos_nombres}')
    else:
        # No está en la lista de activos -> debe ser cesado
        if p.estado == 'Activo':
            p.estado = 'Cesado'
            p.motivo_cese = 'TERMINO DE CONTRATO'
            p.save()
            corregidos_cesado += 1
            print(f'  CESADO: {dni} {p.apellidos_nombres}')

print(f'\nCorregidos a Cesado: {corregidos_cesado}')
print(f'Corregidos a Activo: {corregidos_activo}')
print(f'\nEstado final:')
print(f'  Activos: {Personal.objects.filter(estado="Activo").count()}')
print(f'  Cesados: {Personal.objects.filter(estado="Cesado").count()}')
print(f'  Total: {Personal.objects.count()}')
