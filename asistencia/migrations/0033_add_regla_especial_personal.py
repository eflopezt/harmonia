"""
Agrega modelo ReglaEspecialPersonal para reglas de excepción recurrentes
por empleado (ej: "sábados siempre DL").

También agrega REGLA_ESPECIAL y DESCANSO_SEMANAL a las choices de fuente_codigo.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('personal', '0001_initial'),
        ('tareo', '0032_add_staff_dedup_index'),
    ]

    operations = [
        # Actualizar choices de fuente_codigo en RegistroTareo
        migrations.AlterField(
            model_name='registrotareo',
            name='fuente_codigo',
            field=models.CharField(
                choices=[
                    ('RELOJ', 'Sistema de Asistencia'),
                    ('PAPELETA', 'Papeleta de Permiso/Ausencia'),
                    ('FERIADO', 'Feriado del Calendario'),
                    ('FALTA_AUTO', 'Falta Automática (sin marca ni papeleta)'),
                    ('MANUAL', 'Corrección Manual'),
                    ('REGLA_ESPECIAL', 'Regla Especial por Empleado'),
                    ('DESCANSO_SEMANAL', 'Descanso Semanal Automático'),
                ],
                default='RELOJ',
                max_length=30,
                verbose_name='Fuente del Código',
            ),
        ),
        # Crear modelo ReglaEspecialPersonal
        migrations.CreateModel(
            name='ReglaEspecialPersonal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dias_semana', models.JSONField(blank=True, default=list, help_text='Lista de enteros: 0=Lun..6=Dom. Vacío = todos los días.', verbose_name='Días de la semana')),
                ('condicion_laboral', models.CharField(blank=True, default='', help_text='LOCAL, FORÁNEO, LIMA. Vacío = cualquiera.', max_length=20, verbose_name='Condición laboral')),
                ('codigo_reloj_trigger', models.CharField(blank=True, default='', help_text='Solo aplica si el reloj muestra este código. Vacío = cualquiera.', max_length=20, verbose_name='Código reloj trigger')),
                ('solo_feriados', models.BooleanField(default=False, help_text='Si True, solo aplica cuando el día es feriado.', verbose_name='Solo en feriados')),
                ('fecha_desde', models.DateField(verbose_name='Vigente desde')),
                ('fecha_hasta', models.DateField(blank=True, help_text='Dejar vacío = vigencia indefinida.', null=True, verbose_name='Vigente hasta')),
                ('codigo_resultado', models.CharField(help_text='Código de asistencia a aplicar: DL, FA, DS, T, VAC, etc.', max_length=10, verbose_name='Código resultante')),
                ('horas_override', models.DecimalField(blank=True, decimal_places=2, help_text='Si se especifica, overridea las horas calculadas.', max_digits=5, null=True, verbose_name='Horas override')),
                ('descripcion', models.CharField(help_text='Descripción corta para la tabla.', max_length=300, verbose_name='Descripción')),
                ('descripcion_natural', models.TextField(blank=True, default='', help_text='Texto original que el usuario escribió en el chat IA.', verbose_name='Descripción original')),
                ('conversacion_ia', models.JSONField(blank=True, default=list, help_text='Historial del chat que generó esta regla (auditoría).', verbose_name='Conversación IA')),
                ('prioridad', models.PositiveSmallIntegerField(default=10, help_text='Menor número = mayor prioridad. Primera regla que matchea gana.', verbose_name='Prioridad')),
                ('activa', models.BooleanField(default=True, verbose_name='Activa')),
                ('aplicar_retroactivamente', models.BooleanField(default=False, help_text='Si True, al guardar se recalculan registros pasados.', verbose_name='Aplicar retroactivamente')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reglas_asistencia_creadas', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('personal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reglas_asistencia', to='personal.personal', verbose_name='Empleado')),
            ],
            options={
                'verbose_name': 'Regla Especial de Asistencia',
                'verbose_name_plural': 'Reglas Especiales de Asistencia',
                'ordering': ['personal', 'prioridad'],
            },
        ),
    ]
