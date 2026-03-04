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
