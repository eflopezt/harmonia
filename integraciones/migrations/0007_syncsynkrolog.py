"""Bitácora de sincronización con Synkro RRHH."""
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('integraciones', '0006_whatsapp_plataforma'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncSynkroLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iniciado_en', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('finalizado_en', models.DateTimeField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('OK', 'Completada'), ('ERROR', 'Error'), ('EN_PROGRESO', 'En progreso')], default='EN_PROGRESO', max_length=15)),
                ('origen', models.CharField(choices=[('AUTO', 'Automática (Celery Beat)'), ('MANUAL', 'Manual (usuario)'), ('CLI', 'Comando CLI')], default='AUTO', max_length=10)),
                ('cursor_papeletas', models.DateTimeField(blank=True, help_text='max(FechaRegistro/FechaModifica) procesado en PermisosLicencias', null=True)),
                ('cursor_picados', models.DateTimeField(blank=True, help_text='max(Fecha) procesado en PicadosPersonal', null=True)),
                ('feriados_creados', models.IntegerField(default=0)),
                ('papeletas_creadas', models.IntegerField(default=0)),
                ('papeletas_actualizadas', models.IntegerField(default=0)),
                ('papeletas_omitidas', models.IntegerField(default=0)),
                ('registros_tareo_creados', models.IntegerField(default=0)),
                ('registros_tareo_actualizados', models.IntegerField(default=0)),
                ('personas_no_encontradas', models.IntegerField(default=0, help_text='DNIs de Synkro sin match en Personal de Harmoni')),
                ('duracion_segundos', models.FloatField(default=0)),
                ('error_mensaje', models.TextField(blank=True)),
                ('detalle', models.JSONField(blank=True, default=dict)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='syncs_synkro', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Sync Synkro',
                'verbose_name_plural': 'Sync Synkro',
                'ordering': ['-iniciado_en'],
            },
        ),
    ]
