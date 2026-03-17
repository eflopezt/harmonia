# Generated migration for WhatsApp config fields on Empresa

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0003_empresa_subdominio'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_provider',
            field=models.CharField(
                choices=[('NONE', 'Sin WhatsApp'), ('META_CLOUD', 'Meta Cloud API'), ('OPENCLAW', 'OpenClaw Gateway')],
                default='NONE', max_length=12, verbose_name='Proveedor WhatsApp',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_access_token',
            field=models.CharField(
                blank=True, default='', max_length=500,
                verbose_name='WhatsApp Access Token',
                help_text='Token permanente de la Meta Business App (solo para Meta Cloud API)',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='whatsapp_phone_id',
            field=models.CharField(
                blank=True, default='', max_length=100,
                verbose_name='WhatsApp Phone Number ID',
                help_text='ID del numero en Meta Developer Console (no el numero real)',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='openclaw_gateway_url',
            field=models.CharField(
                blank=True, default='http://localhost:19000', max_length=200,
                verbose_name='OpenClaw Gateway URL',
                help_text='URL del gateway OpenClaw (default: http://localhost:19000)',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='openclaw_gateway_token',
            field=models.CharField(
                blank=True, default='', max_length=200,
                verbose_name='OpenClaw Gateway Token',
                help_text='Token de autenticacion para OpenClaw (si aplica)',
            ),
        ),
    ]
