from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_permisomodulo'),
    ]

    operations = [
        migrations.CreateModel(
            name='PerfilAcceso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre del Perfil')),
                ('codigo', models.SlugField(max_length=50, unique=True, verbose_name='Código')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('es_sistema', models.BooleanField(default=False, help_text='Los perfiles del sistema no se pueden eliminar.', verbose_name='Perfil del sistema')),
                ('mod_personal', models.BooleanField(default=True, verbose_name='Personal')),
                ('mod_asistencia', models.BooleanField(default=True, verbose_name='Asistencia & Tareo')),
                ('mod_vacaciones', models.BooleanField(default=True, verbose_name='Vacaciones')),
                ('mod_documentos', models.BooleanField(default=True, verbose_name='Documentos')),
                ('mod_capacitaciones', models.BooleanField(default=True, verbose_name='Capacitaciones')),
                ('mod_disciplinaria', models.BooleanField(default=False, verbose_name='Disciplinaria')),
                ('mod_evaluaciones', models.BooleanField(default=False, verbose_name='Evaluaciones')),
                ('mod_encuestas', models.BooleanField(default=True, verbose_name='Encuestas')),
                ('mod_salarios', models.BooleanField(default=False, verbose_name='Salarios')),
                ('mod_reclutamiento', models.BooleanField(default=False, verbose_name='Reclutamiento')),
                ('mod_prestamos', models.BooleanField(default=True, verbose_name='Préstamos')),
                ('mod_viaticos', models.BooleanField(default=False, verbose_name='Viáticos')),
                ('mod_onboarding', models.BooleanField(default=False, verbose_name='Onboarding')),
                ('mod_calendario', models.BooleanField(default=True, verbose_name='Calendario')),
                ('mod_analytics', models.BooleanField(default=False, verbose_name='Analytics')),
                ('mod_configuracion', models.BooleanField(default=False, verbose_name='Configuración')),
                ('mod_roster', models.BooleanField(default=False, verbose_name='Roster')),
                ('puede_aprobar', models.BooleanField(default=False, help_text='Habilita botones de aprobación en vacaciones, permisos, roster, etc.', verbose_name='Puede aprobar solicitudes')),
                ('puede_exportar', models.BooleanField(default=True, help_text='Habilita botones de exportación a Excel/PDF en todas las vistas.', verbose_name='Puede exportar datos')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Perfil de Acceso',
                'verbose_name_plural': 'Perfiles de Acceso',
                'ordering': ['nombre'],
            },
        ),
    ]
