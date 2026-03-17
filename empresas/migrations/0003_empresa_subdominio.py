"""
Add subdominio field for multi-tenant subdomain routing.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0002_add_smtp_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='subdominio',
            field=models.SlugField(
                blank=True,
                help_text='Subdominio para acceso (ej: miempresa → miempresa.harmoni.pe)',
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddIndex(
            model_name='empresa',
            index=models.Index(
                fields=['subdominio'],
                name='empresa_subdominio_idx',
            ),
        ),
    ]
