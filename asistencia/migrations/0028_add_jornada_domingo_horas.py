from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tareo', '0027_add_compensacion_feriado'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsistema',
            name='jornada_domingo_horas',
            field=models.DecimalField(
                decimal_places=1,
                default=Decimal('4.0'),
                help_text='Ej: 4.0 para domingos trabajados (LOCAL y FORÁNEO)',
                max_digits=4,
                verbose_name='Jornada Domingo (h/día)',
            ),
        ),
    ]
