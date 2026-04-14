from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('personal', '0001_initial'),
        ('nominas', '0005_add_missing_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecargaAlimentacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveSmallIntegerField(verbose_name='Año')),
                ('mes', models.PositiveSmallIntegerField(verbose_name='Mes')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto Recarga')),
                ('comision', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Comisión Proveedor')),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Total (monto + comisión)')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente de Procesamiento'), ('PROCESADA', 'Procesada (enviada al proveedor)'), ('RECHAZADA', 'Rechazada')], default='PENDIENTE', max_length=15)),
                ('proveedor', models.CharField(default='EDENRED', help_text='Edenred, Sodexo, etc.', max_length=50, verbose_name='Proveedor')),
                ('numero_tarjeta', models.CharField(blank=True, default='', max_length=30)),
                ('procesado_en', models.DateTimeField(blank=True, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('personal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recargas_alimentacion', to='personal.personal')),
            ],
            options={
                'verbose_name': 'Recarga de Alimentación',
                'verbose_name_plural': 'Recargas de Alimentación',
                'ordering': ['-anio', '-mes', 'personal__apellidos_nombres'],
                'unique_together': {('personal', 'anio', 'mes')},
            },
        ),
    ]
