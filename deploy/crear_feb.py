import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from personal.models import Personal, Area, SubArea
from empresas.models import Empresa
from decimal import Decimal

empresa = Empresa.objects.first()
nuevos = [
    {'dni': '44874550', 'nombre': 'MOTTA COAQUIRA, SHULLIANG ASUNCION', 'cargo': 'Asistente Administrativo', 'area': 'ADMINISTRACION'},
    {'dni': '73012587', 'nombre': 'VILLEGAS SANCHEZ, KATHERINE GIOVANA', 'cargo': 'Responsable de Calidad', 'area': 'CALIDAD'},
]
for n in nuevos:
    if Personal.objects.filter(nro_doc=n['dni']).exists():
        print(f"Ya existe: {n['dni']}")
        continue
    area, _ = Area.objects.get_or_create(nombre=n['area'])
    sub, _ = SubArea.objects.get_or_create(nombre='General', area=area)
    Personal.objects.create(
        nro_doc=n['dni'], tipo_doc='DNI',
        apellidos_nombres=n['nombre'],
        cargo=n['cargo'], subarea=sub,
        estado='Activo', empresa=empresa,
        tipo_contrato='PLAZO_FIJO', tipo_trab='Empleado',
        sueldo_base=Decimal('0'),
    )
    print(f"Creado: {n['dni']} {n['nombre']}")
print(f'Total Personal: {Personal.objects.count()}')
