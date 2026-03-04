from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class FlujoTrabajo(models.Model):
    """Definicion de un flujo de aprobacion N-etapas configurable."""
    nombre      = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    icono       = models.CharField(max_length=50, default='fa-code-branch')
    content_type    = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        verbose_name='Modelo',
        help_text='Modelo Django que activa este flujo (ej: SolicitudVacacion)',
    )
    campo_trigger   = models.CharField(max_length=50, default='estado')
    valor_trigger   = models.CharField(max_length=100)
    campo_resultado  = models.CharField(max_length=50, default='estado')
    valor_aprobado   = models.CharField(max_length=100, default='Aprobado')
    valor_rechazado  = models.CharField(max_length=100, default='Rechazado')
    activo           = models.BooleanField(default=True)
    notificar_email  = models.BooleanField(default=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Flujo de Trabajo'
        verbose_name_plural = 'Flujos de Trabajo'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def total_etapas(self):
        return self.etapas.count()


class EtapaFlujo(models.Model):
    """Una etapa (paso) dentro de un FlujoTrabajo."""
    TIPO_APROBADOR = [
        ('SUPERUSER',     'Cualquier administrador RRHH'),
        ('USUARIO',       'Usuario especifico'),
        ('JEFE_AREA',     'Jefe del area del solicitante'),
        ('GRUPO_DJANGO',  'Grupo de Django (rol)'),
    ]
    ACCION_VENCIMIENTO = [
        ('ESPERAR',       'No tomar accion (esperar)'),
        ('AUTO_APROBAR',  'Auto-aprobar al vencer'),
        ('AUTO_RECHAZAR', 'Auto-rechazar al vencer'),
        ('ESCALAR',       'Escalar a usuario alterno'),
    ]

    flujo  = models.ForeignKey(FlujoTrabajo, on_delete=models.CASCADE,
                               related_name='etapas')
    orden  = models.PositiveSmallIntegerField(default=1)
    nombre = models.CharField(max_length=150,
                              help_text='Ej: Aprobacion Jefe Inmediato')
    descripcion = models.TextField(blank=True)
    tipo_aprobador    = models.CharField(max_length=20, choices=TIPO_APROBADOR,
                                         default='SUPERUSER')
    aprobador_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='etapas_como_aprobador',
        help_text='Solo si tipo_aprobador = USUARIO',
    )
    aprobador_grupo   = models.ForeignKey(
        'auth.Group', on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Solo si tipo_aprobador = GRUPO_DJANGO',
    )
    tiempo_limite_horas = models.PositiveIntegerField(
        default=72,
        help_text='Horas antes de aplicar la accion por vencimiento (0 = sin limite)',
    )
    accion_vencimiento  = models.CharField(max_length=15, choices=ACCION_VENCIMIENTO,
                                            default='ESPERAR')
    escalar_a           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        help_text='Solo si accion_vencimiento = ESCALAR',
    )
    requiere_comentario            = models.BooleanField(default=False)
    notificar_solicitante_al_decidir = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Etapa de Flujo'
        verbose_name_plural = 'Etapas de Flujo'
        ordering            = ['flujo', 'orden']
        unique_together     = [['flujo', 'orden']]

    def __str__(self):
        return f'{self.flujo} - Etapa {self.orden}: {self.nombre}'

    def get_aprobadores(self, objeto=None):
        """Retorna la lista de Users que pueden aprobar esta etapa."""
        from django.contrib.auth.models import User
        if self.tipo_aprobador == 'SUPERUSER':
            return list(User.objects.filter(is_superuser=True, is_active=True))
        elif self.tipo_aprobador == 'USUARIO':
            return [self.aprobador_usuario] if self.aprobador_usuario else []
        elif self.tipo_aprobador == 'GRUPO_DJANGO':
            if self.aprobador_grupo:
                return list(self.aprobador_grupo.user_set.filter(is_active=True))
            return []
        elif self.tipo_aprobador == 'JEFE_AREA' and objeto:
            try:
                personal = getattr(objeto, 'personal', None) or getattr(objeto, 'empleado', None)
                if personal and personal.subarea and personal.subarea.area:
                    jefe = personal.subarea.area.jefe
                    if jefe and jefe.usuario:
                        return [jefe.usuario]
            except Exception:
                pass
            return list(User.objects.filter(is_superuser=True, is_active=True))
        return []


class InstanciaFlujo(models.Model):
    """Ejecucion en tiempo real de un FlujoTrabajo para un objeto especifico."""
    ESTADO_CHOICES = [
        ('EN_PROCESO', 'En proceso'),
        ('APROBADO',   'Aprobado'),
        ('RECHAZADO',  'Rechazado'),
        ('CANCELADO',  'Cancelado'),
        ('VENCIDO',    'Vencido'),
    ]
    flujo        = models.ForeignKey(FlujoTrabajo, on_delete=models.CASCADE,
                                     related_name='instancias')
    etapa_actual = models.ForeignKey(EtapaFlujo, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='instancias_en_esta_etapa')
    estado       = models.CharField(max_length=15, choices=ESTADO_CHOICES,
                                    default='EN_PROCESO', db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    objeto       = GenericForeignKey('content_type', 'object_id')
    solicitante  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='flujos_solicitados',
    )
    iniciado_en      = models.DateTimeField(auto_now_add=True)
    completado_en    = models.DateTimeField(null=True, blank=True)
    etapa_vence_en   = models.DateTimeField(null=True, blank=True)
    metadata         = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name        = 'Instancia de Flujo'
        verbose_name_plural = 'Instancias de Flujo'
        ordering            = ['-iniciado_en']
        indexes             = [
            models.Index(fields=['estado', 'iniciado_en'], name='wf_estado_fecha_idx'),
            models.Index(fields=['content_type', 'object_id'], name='wf_objeto_idx'),
        ]

    def __str__(self):
        return f'{self.flujo} #{self.pk} - {self.estado}'

    @property
    def color_estado(self):
        return {
            'EN_PROCESO': 'warning',
            'APROBADO':   'success',
            'RECHAZADO':  'danger',
            'CANCELADO':  'secondary',
            'VENCIDO':    'muted',
        }.get(self.estado, 'secondary')

    @property
    def icono_estado(self):
        return {
            'EN_PROCESO': 'fa-clock',
            'APROBADO':   'fa-check-circle',
            'RECHAZADO':  'fa-times-circle',
            'CANCELADO':  'fa-ban',
            'VENCIDO':    'fa-calendar-times',
        }.get(self.estado, 'fa-question')

    def get_siguiente_etapa(self):
        if not self.etapa_actual:
            return self.flujo.etapas.order_by('orden').first()
        try:
            return self.flujo.etapas.filter(
                orden__gt=self.etapa_actual.orden
            ).order_by('orden').first()
        except Exception:
            return None

    def puede_aprobar(self, usuario):
        if not self.etapa_actual or self.estado != 'EN_PROCESO':
            return False
        aprobadores = self.etapa_actual.get_aprobadores(self.objeto)
        return any(a.pk == usuario.pk for a in aprobadores)


class PasoFlujo(models.Model):
    """Registro inmutable de cada decision tomada en un flujo."""
    DECISION_CHOICES = [
        ('APROBADO',        'Aprobado'),
        ('RECHAZADO',       'Rechazado'),
        ('DELEGADO',        'Delegado'),
        ('AUTO_APROBADO',   'Auto-aprobado (timeout)'),
        ('AUTO_RECHAZADO',  'Auto-rechazado (timeout)'),
        ('CANCELADO',       'Cancelado'),
    ]
    instancia  = models.ForeignKey(InstanciaFlujo, on_delete=models.CASCADE,
                                   related_name='pasos')
    etapa      = models.ForeignKey(EtapaFlujo, on_delete=models.SET_NULL, null=True)
    aprobador  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='+',
    )
    decision   = models.CharField(max_length=20, choices=DECISION_CHOICES)
    comentario = models.TextField(blank=True)
    fecha      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Paso de Flujo'
        verbose_name_plural = 'Pasos de Flujo'
        ordering            = ['instancia', 'fecha']

    def __str__(self):
        return f'{self.instancia} - {self.get_decision_display()} por {self.aprobador}'
