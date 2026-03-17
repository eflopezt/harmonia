# Generated migration for WhatsApp notification support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comunicaciones', '0002_add_missing_indexes'),
    ]

    operations = [
        # Add WHATSAPP to Notificacion.tipo choices (no DB change needed for choices,
        # but we add the telefono field)
        migrations.AddField(
            model_name='notificacion',
            name='destinatario_telefono',
            field=models.CharField(
                blank=True, default='', max_length=20,
                verbose_name='Telefono destinatario',
                help_text='Numero WhatsApp en formato internacional sin \'+\' (ej: 51999888777)',
            ),
        ),
        # Add recibir_whatsapp to PreferenciaNotificacion
        migrations.AddField(
            model_name='preferencianotificacion',
            name='recibir_whatsapp',
            field=models.BooleanField(default=True, verbose_name='Recibir WhatsApp'),
        ),
    ]
