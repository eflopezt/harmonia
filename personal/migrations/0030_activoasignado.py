from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('personal', '0028_populate_cargo_from_personal'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivoAsignado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('LAPTOP', 'Laptop / Computador'), ('CELULAR', 'Celular / Smartphone'), ('RADIO', 'Radio / Walkie-Talkie'), ('TABLET', 'Tablet'), ('HERRAMIENTA', 'Herramienta de Trabajo'), ('VEHICULO', 'Vehículo'), ('LLAVE', 'Llave / Tarjeta de Acceso'), ('MOBILIARIO', 'Mobiliario de Oficina'), ('OTRO', 'Otro')], max_length=20, verbose_name='Tipo de Activo')),
                ('descripcion', models.CharField(help_text='Ej: Laptop Dell Latitude 5520, S/N ABC123', max_length=200, verbose_name='Descripción')),
                ('serial', models.CharField(blank=True, default='', max_length=100, verbose_name='N° Serie / Código')),
                ('fecha_asignacion', models.DateField(verbose_name='Fecha de Asignación')),
                ('fecha_devolucion', models.DateField(blank=True, null=True, verbose_name='Fecha de Devolución')),
                ('estado', models.CharField(choices=[('ASIGNADO', 'Asignado al trabajador'), ('DEVUELTO', 'Devuelto'), ('EXTRAVIADO', 'Extraviado / Perdido'), ('DANADO', 'Dañado')], default='ASIGNADO', max_length=15)),
                ('valor_estimado', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Valor Estimado (S/)')),
                ('observaciones', models.TextField(blank=True, default='')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('personal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activos_asignados', to='personal.personal', verbose_name='Trabajador')),
                ('registrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activos_registrados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Activo Asignado',
                'verbose_name_plural': 'Activos Asignados',
                'ordering': ['-fecha_asignacion'],
            },
        ),
    ]
