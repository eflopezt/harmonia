from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tareo', '0026_add_jornada_sabado_horas'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompensacionFeriado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_feriado', models.DateField(
                    help_text='Día oficial de feriado que se traslada (se trabaja normalmente).',
                    verbose_name='Fecha del Feriado Original',
                )),
                ('fecha_compensada', models.DateField(
                    help_text='Día que toma el tratamiento de feriado en sustitución.',
                    verbose_name='Fecha Compensada (nuevo feriado)',
                )),
                ('descripcion', models.CharField(
                    blank=True,
                    help_text="Ej: 'Feriado 02-Abr trasladado al 04-Abr por D.S. 012-2026'",
                    max_length=200,
                    verbose_name='Descripción',
                )),
                ('activo', models.BooleanField(
                    default=True,
                    help_text='Desactivar sin borrar si el traslado fue revertido.',
                    verbose_name='Activo',
                )),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Compensación de Feriado',
                'verbose_name_plural': 'Compensaciones de Feriado',
                'ordering': ['fecha_feriado'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='compensacionferiado',
            unique_together={('fecha_feriado', 'fecha_compensada')},
        ),
    ]
