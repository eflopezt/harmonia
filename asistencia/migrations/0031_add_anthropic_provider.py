"""
Agrega ANTHROPIC como opción válida en ia_provider (IA_PROVIDER_CHOICES).
Solo cambia choices en el campo — no altera datos existentes.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tareo', '0030_set_dia_corte_21'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracionsistema',
            name='ia_provider',
            field=models.CharField(
                choices=[
                    ('GEMINI', 'Gemini (Google — recomendado)'),
                    ('DEEPSEEK', 'DeepSeek (más económico)'),
                    ('OPENAI', 'OpenAI (GPT-4o-mini)'),
                    ('ANTHROPIC', 'Anthropic (Claude)'),
                    ('OLLAMA', 'Ollama (Local — sin costo)'),
                    ('NINGUNO', 'Sin IA'),
                ],
                default='NINGUNO',
                help_text='Proveedor para chat, análisis y mapeo de columnas',
                max_length=20,
                verbose_name='Proveedor de IA (Chat/RAG)',
            ),
        ),
    ]
