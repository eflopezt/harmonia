"""
Migration: Add DashboardLayout model for customizable drag-and-drop dashboard.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('analytics', '0003_dashboard_widget'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardLayout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('widget_ids', models.JSONField(default=list, help_text='Lista ordenada de widget_id strings del catalogo', verbose_name='IDs de widgets activos')),
                ('config', models.JSONField(default=dict, help_text='Tamanos personalizados, columnas, etc.', verbose_name='Configuracion extra')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_layout', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Layout Dashboard',
                'verbose_name_plural': 'Layouts Dashboard',
            },
        ),
    ]
