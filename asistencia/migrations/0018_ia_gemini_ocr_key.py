"""
Fase 4.4 — campo ia_gemini_api_key.

Permite configurar una API key de Gemini exclusivamente para OCR,
independiente de la key del proveedor principal (ej: DeepSeek para chat
+ Gemini para OCR de PDFs escaneados).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tareo', '0017_ia_multi_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsistema',
            name='ia_gemini_api_key',
            field=models.CharField(
                blank=True,
                default='',
                max_length=500,
                verbose_name='API Key Gemini (OCR)',
                help_text=(
                    'Clave API de Gemini exclusiva para OCR de PDFs escaneados. '
                    'Permite usar DeepSeek para chat y Gemini para OCR simultáneamente. '
                    'Si está vacía y el proveedor principal es Gemini, se usa ia_api_key.'
                ),
            ),
        ),
    ]
