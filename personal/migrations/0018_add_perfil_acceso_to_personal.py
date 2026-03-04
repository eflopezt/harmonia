import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personal', '0017_add_empresa_fk'),
        ('core', '0004_add_perfil_acceso'),
    ]

    operations = [
        migrations.AddField(
            model_name='personal',
            name='perfil_acceso',
            field=models.ForeignKey(
                blank=True,
                help_text='Define qué módulos del sistema puede ver este usuario. Dejar vacío si el usuario no tiene cuenta de sistema, o si es superusuario (acceso total siempre).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='usuarios_asignados',
                to='core.perfilacceso',
                verbose_name='Perfil de Acceso',
            ),
        ),
    ]
