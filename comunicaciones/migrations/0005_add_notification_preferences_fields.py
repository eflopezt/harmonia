"""
Add per-type and per-channel notification preference fields.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comunicaciones', '0004_whatsapp_templates'),
    ]

    operations = [
        # ── Per-channel ──
        migrations.AddField(
            model_name='preferencianotificacion',
            name='recibir_push',
            field=models.BooleanField(default=True, verbose_name='Recibir push en navegador'),
        ),
        # ── Per-type toggles ──
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_vacaciones',
            field=models.BooleanField(default=True, verbose_name='Vacaciones'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_nominas',
            field=models.BooleanField(default=True, verbose_name='Nominas / Boletas'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_workflows',
            field=models.BooleanField(default=True, verbose_name='Aprobaciones / Workflows'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_asistencia',
            field=models.BooleanField(default=True, verbose_name='Asistencia / Tareo'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_comunicados',
            field=models.BooleanField(default=True, verbose_name='Comunicados'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_sistema',
            field=models.BooleanField(default=True, verbose_name='Sistema / Alertas'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_evaluaciones',
            field=models.BooleanField(default=True, verbose_name='Evaluaciones'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_capacitaciones',
            field=models.BooleanField(default=True, verbose_name='Capacitaciones'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_disciplinaria',
            field=models.BooleanField(default=True, verbose_name='Disciplinaria'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='notif_onboarding',
            field=models.BooleanField(default=True, verbose_name='Onboarding'),
        ),
        # ── Behavior ──
        migrations.AddField(
            model_name='preferencianotificacion',
            name='sonido_habilitado',
            field=models.BooleanField(default=True, verbose_name='Sonido de notificacion'),
        ),
        migrations.AddField(
            model_name='preferencianotificacion',
            name='toast_habilitado',
            field=models.BooleanField(default=True, verbose_name='Toast emergente'),
        ),
    ]
