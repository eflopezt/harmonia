"""
Migración de datos: establece dia_corte_planilla=21 en ConfiguracionSistema.
Esto hace que el ciclo de planilla sea del 22 del mes anterior al 21 del mes actual.
"""
from django.db import migrations


def set_corte_21(apps, schema_editor):
    ConfiguracionSistema = apps.get_model('tareo', 'ConfiguracionSistema')
    obj = ConfiguracionSistema.objects.filter(pk=1).first()
    if obj:
        obj.dia_corte_planilla = 21
        obj.save(update_fields=['dia_corte_planilla'])
    else:
        # Si no existe configuración aún, la creamos con el valor correcto
        ConfiguracionSistema.objects.create(pk=1, dia_corte_planilla=21)


def revert_corte(apps, schema_editor):
    ConfiguracionSistema = apps.get_model('tareo', 'ConfiguracionSistema')
    obj = ConfiguracionSistema.objects.filter(pk=1).first()
    if obj:
        obj.dia_corte_planilla = 20
        obj.save(update_fields=['dia_corte_planilla'])


class Migration(migrations.Migration):

    dependencies = [
        ('tareo', '0029_add_almuerzo_manual'),
    ]

    operations = [
        migrations.RunPython(set_corte_21, revert_corte),
    ]
