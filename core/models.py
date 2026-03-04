"""
Modelos transversales del sistema Harmoni.

AuditLog: registro automático de cambios en modelos críticos.
PreferenciaUsuario: configuración personalizada por usuario.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    """Registro de auditoría genérico para cualquier modelo del sistema.

    Captura CREATE, UPDATE y DELETE con detalle de campos modificados.
    """

    ACCION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Modificación'),
        ('DELETE', 'Eliminación'),
    ]

    # Referencia genérica al objeto modificado
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Qué pasó
    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    descripcion = models.CharField(
        max_length=255, blank=True,
        help_text='Resumen legible del cambio.',
    )

    # Detalle de cambios (solo para UPDATE)
    cambios = models.JSONField(
        default=dict, blank=True,
        help_text='Dict con {campo: {old: ..., new: ...}} para cada campo modificado.',
    )

    # Quién lo hizo
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Cuándo
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['usuario', '-timestamp']),
            models.Index(fields=['accion', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.get_accion_display()} · {self.content_type} #{self.object_id}'


class PreferenciaUsuario(models.Model):
    """Preferencias personalizadas por usuario (singleton por user).

    Se crea automáticamente con get_or_create la primera vez que se necesita.
    """

    ITEMS_PAGINA_CHOICES = [
        (10, '10 por página'),
        (20, '20 por página'),
        (30, '30 por página'),
        (50, '50 por página'),
    ]

    TEMA_CHOICES = [
        ('AUTO', 'Sistema (auto)'),
        ('LIGHT', 'Claro'),
        ('DARK', 'Oscuro'),
    ]

    IDIOMA_CHOICES = [
        ('es', 'Español'),
        ('en', 'English'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferencias',
        verbose_name='Usuario',
    )

    # ── Interfaz ──────────────────────────────────────────────────────
    sidebar_colapsado = models.BooleanField(
        default=False,
        verbose_name='Sidebar colapsado por defecto',
    )
    items_por_pagina = models.PositiveSmallIntegerField(
        default=20,
        choices=ITEMS_PAGINA_CHOICES,
        verbose_name='Elementos por página',
    )
    tema = models.CharField(
        max_length=6,
        choices=TEMA_CHOICES,
        default='AUTO',
        verbose_name='Tema de color',
    )
    idioma = models.CharField(
        max_length=5,
        choices=IDIOMA_CHOICES,
        default='es',
        verbose_name='Idioma',
    )

    # ── Notificaciones ────────────────────────────────────────────────
    notif_email_habilitado = models.BooleanField(
        default=True,
        verbose_name='Recibir notificaciones por email',
    )
    notif_contratos = models.BooleanField(
        default=True,
        verbose_name='Alertas de contratos y período de prueba',
    )
    notif_vacaciones = models.BooleanField(
        default=True,
        verbose_name='Alertas de vacaciones',
    )
    notif_documentos = models.BooleanField(
        default=True,
        verbose_name='Alertas de documentos laborales',
    )

    # ── Dashboard ────────────────────────────────────────────────────
    dashboard_widgets = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Widgets del dashboard activos',
        help_text='Lista de slugs de widgets que el usuario quiere ver en su home.',
    )

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Preferencia de Usuario'
        verbose_name_plural = 'Preferencias de Usuarios'

    def __str__(self):
        return f'Preferencias de {self.usuario}'

    @classmethod
    def para(cls, user):
        """Retorna (o crea) las preferencias del usuario dado."""
        prefs, _ = cls.objects.get_or_create(usuario=user)
        return prefs


# ─────────────────────────────────────────────────────────────────────
# PermisoModulo — Permisos granulares por módulo (INFRA.3)
# ─────────────────────────────────────────────────────────────────────

MODULOS_SISTEMA = [
    ('personal',        'Personal'),
    ('asistencia',      'Asistencia & Tareo'),
    ('nominas',         'Nóminas'),
    ('vacaciones',      'Vacaciones & Permisos'),
    ('documentos',      'Documentos'),
    ('capacitaciones',  'Capacitaciones'),
    ('disciplinaria',   'Disciplinaria'),
    ('evaluaciones',    'Evaluaciones'),
    ('encuestas',       'Encuestas'),
    ('salarios',        'Salarios'),
    ('reclutamiento',   'Reclutamiento'),
    ('comunicaciones',  'Comunicaciones'),
    ('prestamos',       'Préstamos'),
    ('viaticos',        'Viáticos'),
    ('onboarding',      'Onboarding'),
    ('calendario',      'Calendario'),
    ('analytics',       'Analytics'),
    ('configuracion',   'Configuración'),
]


class PermisoModulo(models.Model):
    """
    Permisos granulares por módulo para usuarios no-superusuarios.
    Los superusuarios siempre tienen acceso total (bypass).
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='permisos_modulos',
        verbose_name='Usuario',
    )
    modulo = models.CharField(
        max_length=30,
        choices=MODULOS_SISTEMA,
        verbose_name='Módulo',
    )
    puede_ver     = models.BooleanField(default=False, verbose_name='Ver')
    puede_crear   = models.BooleanField(default=False, verbose_name='Crear')
    puede_editar  = models.BooleanField(default=False, verbose_name='Editar')
    puede_aprobar = models.BooleanField(default=False, verbose_name='Aprobar')
    puede_exportar= models.BooleanField(default=False, verbose_name='Exportar')

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['usuario', 'modulo']
        verbose_name = 'Permiso de Módulo'
        verbose_name_plural = 'Permisos de Módulos'
        ordering = ['usuario', 'modulo']

    def __str__(self):
        return f'{self.usuario} — {self.get_modulo_display()}'
