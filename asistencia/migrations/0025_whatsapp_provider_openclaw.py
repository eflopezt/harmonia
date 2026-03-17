# Generated migration for WhatsApp provider + OpenClaw fields on ConfiguracionSistema

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tareo', '0024_add_missing_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsistema',
            name='whatsapp_provider',
            field=models.CharField(
                choices=[('NONE', 'Sin WhatsApp'), ('META_CLOUD', 'Meta Cloud API'), ('OPENCLAW', 'OpenClaw Gateway')],
                default='NONE', max_length=12,
                verbose_name='Proveedor WhatsApp',
                help_text='Seleccione el proveedor para enviar mensajes de WhatsApp.',
            ),
        ),
        migrations.AddField(
            model_name='configuracionsistema',
            name='openclaw_gateway_url',
            field=models.CharField(
                blank=True, default='http://localhost:19000', max_length=200,
                verbose_name='OpenClaw Gateway URL',
                help_text='URL del gateway OpenClaw para envio de WhatsApp.',
            ),
        ),
        migrations.AddField(
            model_name='configuracionsistema',
            name='openclaw_gateway_token',
            field=models.CharField(
                blank=True, default='', max_length=200,
                verbose_name='OpenClaw Gateway Token',
                help_text='Token de autenticacion para OpenClaw (si aplica).',
            ),
        ),
    ]
