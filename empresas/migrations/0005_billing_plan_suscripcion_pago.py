# Generated migration for Billing: Plan, Suscripcion, HistorialPago

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('empresas', '0004_whatsapp_config'),
    ]

    operations = [
        # ── Plan ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Nombre del plan')),
                ('codigo', models.SlugField(max_length=30, unique=True, verbose_name='Código')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('precio_mensual', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Precio mensual (S/)')),
                ('precio_anual', models.DecimalField(blank=True, decimal_places=2, help_text='Precio anual con descuento. Dejar vacío = precio_mensual * 12.', max_digits=10, null=True, verbose_name='Precio anual (S/)')),
                ('max_empleados', models.IntegerField(default=30, help_text='0 = ilimitado', verbose_name='Máx. empleados')),
                ('modulos_incluidos', models.JSONField(blank=True, default=list, help_text='Lista de códigos de módulo (ej: ["nominas", "asistencia", "vacaciones"])', verbose_name='Módulos incluidos')),
                ('features', models.JSONField(blank=True, default=list, help_text='Lista de textos para mostrar en la tarjeta del plan', verbose_name='Características destacadas')),
                ('orden', models.PositiveSmallIntegerField(default=0, help_text='Orden de visualización')),
                ('activo', models.BooleanField(default=True)),
                ('destacado', models.BooleanField(default=False, help_text='Mostrar como "Recomendado" en la página de planes')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Plan',
                'verbose_name_plural': 'Planes',
                'ordering': ['orden', 'precio_mensual'],
            },
        ),
        # ── Suscripcion ──────────────────────────────────────────
        migrations.CreateModel(
            name='Suscripcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('TRIAL', 'Periodo de prueba'), ('ACTIVA', 'Activa'), ('SUSPENDIDA', 'Suspendida'), ('CANCELADA', 'Cancelada')], default='TRIAL', max_length=12)),
                ('ciclo', models.CharField(choices=[('MENSUAL', 'Mensual'), ('ANUAL', 'Anual')], default='MENSUAL', max_length=10)),
                ('fecha_inicio', models.DateField(verbose_name='Fecha de inicio')),
                ('fecha_fin', models.DateField(blank=True, help_text='Null = suscripción vigente sin fecha de término', null=True, verbose_name='Fecha de fin')),
                ('dias_trial', models.IntegerField(default=15, verbose_name='Días de trial')),
                ('proximo_pago', models.DateField(verbose_name='Próximo pago')),
                ('notas', models.TextField(blank=True, verbose_name='Notas internas')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('empresa', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='suscripcion', to='empresas.empresa')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='suscripciones', to='empresas.plan')),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Suscripción',
                'verbose_name_plural': 'Suscripciones',
            },
        ),
        # ── HistorialPago ────────────────────────────────────────
        migrations.CreateModel(
            name='HistorialPago',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto (S/)')),
                ('fecha_pago', models.DateField(verbose_name='Fecha de pago')),
                ('fecha_vencimiento', models.DateField(blank=True, null=True, verbose_name='Fecha de vencimiento')),
                ('metodo_pago', models.CharField(choices=[('YAPE', 'Yape'), ('PLIN', 'Plin'), ('TRANSFERENCIA', 'Transferencia bancaria'), ('TARJETA', 'Tarjeta de crédito/débito'), ('EFECTIVO', 'Efectivo'), ('OTRO', 'Otro')], default='YAPE', max_length=15)),
                ('referencia', models.CharField(blank=True, max_length=100, verbose_name='Nro. referencia / operación')),
                ('comprobante', models.FileField(blank=True, null=True, upload_to='billing/comprobantes/%Y/%m/', verbose_name='Comprobante adjunto')),
                ('comprobante_tipo', models.CharField(choices=[('BOLETA', 'Boleta de venta'), ('FACTURA', 'Factura'), ('RECIBO', 'Recibo')], default='BOLETA', max_length=10, verbose_name='Tipo de comprobante')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('PAGADO', 'Pagado'), ('VENCIDO', 'Vencido'), ('ANULADO', 'Anulado')], default='PENDIENTE', max_length=10)),
                ('periodo_desde', models.DateField(blank=True, null=True, verbose_name='Periodo desde')),
                ('periodo_hasta', models.DateField(blank=True, null=True, verbose_name='Periodo hasta')),
                ('notas', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('suscripcion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagos', to='empresas.suscripcion')),
                ('registrado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pago',
                'verbose_name_plural': 'Historial de pagos',
                'ordering': ['-fecha_pago', '-creado_en'],
            },
        ),
    ]
