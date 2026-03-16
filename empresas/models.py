"""
Empresas — Modelo multi-empresa para Harmoni ERP.

Permite gestionar múltiples empresas (RUC) dentro de la misma instancia.
Cada empresa tiene su propia configuración, personal y nóminas.

Architecture: Row-level tenancy
- Personal.empresa FK → Empresa
- PeriodoNomina.empresa FK → Empresa
- Session: 'empresa_actual_id' → filtra datos por empresa
"""
from django.conf import settings
from django.db import models


class Empresa(models.Model):
    """
    Empresa empleadora (persona jurídica o natural con RUC).

    Una instancia Harmoni puede gestionar múltiples empresas.
    Ejemplo: Holding con subsidiarias, grupo económico, etc.
    """
    REGIMEN_CHOICES = [
        ('GENERAL',  'Régimen General'),
        ('MYPE',     'Régimen MYPE Tributario'),
        ('ESPECIAL', 'Régimen Especial Renta'),
        ('NRUS',     'Nuevo RUS'),
    ]
    SECTOR_CHOICES = [
        ('PRIVADO',   'Privado'),
        ('PUBLICO',   'Público'),
        ('MIXTO',     'Economía mixta'),
        ('SIN_FINES', 'Sin fines de lucro'),
    ]

    ruc              = models.CharField(max_length=11, unique=True, verbose_name='RUC')
    razon_social     = models.CharField(max_length=200, verbose_name='Razón Social')
    nombre_comercial = models.CharField(max_length=200, blank=True, verbose_name='Nombre Comercial')

    # Dirección
    direccion    = models.CharField(max_length=300, blank=True)
    ubigeo       = models.CharField(max_length=6, blank=True, help_text='Código UBIGEO 6 dígitos')
    distrito     = models.CharField(max_length=100, blank=True)
    provincia    = models.CharField(max_length=100, blank=True)
    departamento = models.CharField(max_length=100, blank=True)

    # Contacto
    telefono   = models.CharField(max_length=20, blank=True)
    email_rrhh = models.EmailField(blank=True, verbose_name='Email RRHH')
    web        = models.URLField(blank=True)

    # Clasificación
    regimen_laboral     = models.CharField(max_length=12, choices=REGIMEN_CHOICES, default='GENERAL')
    sector              = models.CharField(max_length=10, choices=SECTOR_CHOICES, default='PRIVADO')
    actividad_economica = models.CharField(max_length=200, blank=True, help_text='CIIU')

    # SUNAT / PLAME
    codigo_empleador = models.CharField(
        max_length=20, blank=True,
        help_text='Código empleador SUNAT (si aplica)'
    )

    # ── Configuración SMTP (email por empresa) ──────────────
    PROVEEDOR_EMAIL_CHOICES = [
        ('GMAIL',     'Gmail (SMTP)'),
        ('OFFICE365',  'Microsoft 365 / Outlook'),
        ('CUSTOM',    'SMTP personalizado'),
        ('NONE',      'Sin correo configurado'),
    ]

    email_proveedor = models.CharField(
        max_length=10, choices=PROVEEDOR_EMAIL_CHOICES,
        default='NONE', verbose_name='Proveedor de correo',
    )
    email_host = models.CharField(
        max_length=200, blank=True, default='',
        help_text='Servidor SMTP (ej: smtp.gmail.com, smtp.office365.com)',
    )
    email_port = models.PositiveSmallIntegerField(
        default=587, help_text='Puerto SMTP (587=TLS, 465=SSL)',
    )
    email_use_tls = models.BooleanField(default=True)
    email_use_ssl = models.BooleanField(default=False)
    email_host_user = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='Usuario SMTP',
        help_text='Email o usuario para autenticación',
    )
    email_host_password = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='Contraseña SMTP',
        help_text='Contraseña o App Password',
    )
    email_from = models.EmailField(
        blank=True, default='',
        verbose_name='Email remitente',
        help_text='Dirección "De:" (ej: rrhh@empresa.com)',
    )
    email_reply_to = models.EmailField(
        blank=True, default='',
        verbose_name='Reply-To',
        help_text='Dirección de respuesta (opcional)',
    )

    # Estado
    activa       = models.BooleanField(default=True)
    es_principal = models.BooleanField(
        default=False,
        help_text='Empresa principal/default del sistema'
    )

    creado_en      = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )

    class Meta:
        verbose_name        = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering            = ['razon_social']
        indexes             = [
            models.Index(fields=['ruc'], name='empresa_ruc_idx'),
            models.Index(fields=['activa', 'es_principal'], name='empresa_activa_idx'),
        ]

    def __str__(self):
        return f'{self.nombre_comercial or self.razon_social} ({self.ruc})'

    def save(self, *args, **kwargs):
        # Solo una empresa puede ser principal
        if self.es_principal:
            Empresa.objects.filter(es_principal=True).exclude(pk=self.pk).update(es_principal=False)
        super().save(*args, **kwargs)
        # Invalidar cache de empresas disponibles en sidebar
        try:
            from personal.context_processors import invalidar_empresas
            invalidar_empresas()
        except Exception:
            pass

    @property
    def nombre_display(self):
        return self.nombre_comercial or self.razon_social

    @property
    def tiene_email_configurado(self):
        return (
            self.email_proveedor != 'NONE'
            and self.email_host
            and self.email_host_user
            and self.email_host_password
        )

    def get_smtp_config(self):
        """Retorna dict con configuración SMTP para esta empresa."""
        if not self.tiene_email_configurado:
            return None
        return {
            'host': self.email_host,
            'port': self.email_port,
            'username': self.email_host_user,
            'password': self.email_host_password,
            'use_tls': self.email_use_tls,
            'use_ssl': self.email_use_ssl,
            'from_email': self.email_from or self.email_host_user,
            'reply_to': self.email_reply_to,
        }

    def auto_fill_smtp(self):
        """Auto-llena host/port según el proveedor seleccionado."""
        SMTP_DEFAULTS = {
            'GMAIL': {'host': 'smtp.gmail.com', 'port': 587, 'tls': True, 'ssl': False},
            'OFFICE365': {'host': 'smtp.office365.com', 'port': 587, 'tls': True, 'ssl': False},
        }
        defaults = SMTP_DEFAULTS.get(self.email_proveedor)
        if defaults and not self.email_host:
            self.email_host = defaults['host']
            self.email_port = defaults['port']
            self.email_use_tls = defaults['tls']
            self.email_use_ssl = defaults['ssl']
