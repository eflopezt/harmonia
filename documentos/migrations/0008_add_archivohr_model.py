from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0007_add_documento_firma_digital'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('personal', '0021_add_missing_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchivoHR',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255, verbose_name='Nombre del archivo')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('archivo', models.FileField(upload_to='archivos_hr/%Y/%m/', verbose_name='Archivo')),
                ('periodo', models.CharField(blank=True, help_text='Período referencial, ej: 2026-03', max_length=7, verbose_name='Período')),
                ('visible', models.BooleanField(default=True, help_text='Si está activo, el trabajador puede verlo y descargarlo.', verbose_name='Visible para el trabajador')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('descargado', models.BooleanField(default=False)),
                ('fecha_descarga', models.DateTimeField(blank=True, null=True)),
                ('personal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='archivos_hr', to='personal.personal', verbose_name='Trabajador')),
                ('subido_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Subido por')),
            ],
            options={
                'verbose_name': 'Archivo HR',
                'verbose_name_plural': 'Archivos HR',
                'ordering': ['-creado_en'],
                'indexes': [models.Index(fields=['personal', '-creado_en'], name='documentos_archivohr_personal_idx')],
            },
        ),
    ]
