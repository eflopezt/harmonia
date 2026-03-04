"""
Módulo de Amonestaciones y Proceso Disciplinario.
Gestiona medidas disciplinarias, descargos y cartas según legislación peruana.

Base legal:
- DS 003-97-TR (TUO DL 728): Art. 24-28 faltas graves, Art. 31 procedimiento despido
- Art. 25: Faltas graves que dan lugar a despido
- Art. 31: Despido requiere carta de preaviso + 6 días hábiles para descargo
- Art. 32: Despido debe indicar causa y fecha de cese
"""
from datetime import date, timedelta

from django.conf import settings
from django.db import models

from personal.models import Personal


class TipoFalta(models.Model):
    """Tipos de falta configurables."""
    nombre = models.CharField(max_length=200, unique=True)
    codigo = models.SlugField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)
    gravedad = models.CharField(
        max_length=10,
        choices=[
            ('LEVE', 'Leve'),
            ('GRAVE', 'Grave'),
            ('MUY_GRAVE', 'Muy Grave'),
        ],
        default='LEVE',
    )
    base_legal = models.CharField(
        max_length=200, blank=True,
        help_text="Referencia legal (ej: DS 003-97-TR Art. 25 inc. a)"
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=10)

    class Meta:
        verbose_name = "Tipo de Falta"
        verbose_name_plural = "Tipos de Falta"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_gravedad_display()})"


class MedidaDisciplinaria(models.Model):
    """Registro de una medida disciplinaria contra un trabajador."""
    TIPO_CHOICES = [
        ('VERBAL', 'Amonestación Verbal'),
        ('ESCRITA', 'Amonestación Escrita'),
        ('SUSPENSION', 'Suspensión'),
        ('DESPIDO', 'Despido'),
    ]
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('NOTIFICADA', 'Notificada'),
        ('EN_DESCARGO', 'En Período de Descargo'),
        ('DESCARGO_RECIBIDO', 'Descargo Recibido'),
        ('RESUELTA', 'Resuelta'),
        ('ANULADA', 'Anulada'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='medidas_disciplinarias', verbose_name="Trabajador"
    )
    tipo_medida = models.CharField(
        max_length=12, choices=TIPO_CHOICES,
        verbose_name="Tipo de Medida"
    )
    tipo_falta = models.ForeignKey(
        TipoFalta, on_delete=models.PROTECT,
        related_name='medidas', verbose_name="Tipo de Falta"
    )

    # Hechos
    fecha_hechos = models.DateField(verbose_name="Fecha de los Hechos")
    descripcion_hechos = models.TextField(verbose_name="Descripción de los Hechos")
    testigos = models.TextField(
        blank=True, verbose_name="Testigos",
        help_text="Nombres de testigos presenciales"
    )
    evidencias = models.FileField(
        upload_to='disciplinaria/evidencias/%Y/%m/',
        blank=True, null=True, verbose_name="Evidencias"
    )

    # Carta de preaviso (para despido - Art. 31 DS 003-97-TR)
    fecha_carta_preaviso = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha Carta Preaviso",
        help_text="Obligatoria para despido — inicia plazo de 6 días hábiles para descargo"
    )
    documento_preaviso = models.FileField(
        upload_to='disciplinaria/cartas/%Y/%m/',
        blank=True, null=True, verbose_name="Carta de Preaviso"
    )

    # Plazo descargo
    fecha_limite_descargo = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha Límite Descargo",
        help_text="6 días hábiles desde notificación (Art. 31 DS 003-97-TR)"
    )

    # Resolución
    fecha_resolucion = models.DateField(null=True, blank=True, verbose_name="Fecha Resolución")
    resolucion = models.TextField(
        blank=True, verbose_name="Resolución",
        help_text="Decisión final tras evaluar el descargo"
    )
    dias_suspension = models.PositiveSmallIntegerField(
        default=0, verbose_name="Días de Suspensión",
        help_text="Solo para tipo SUSPENSION"
    )
    fecha_cese = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha de Cese",
        help_text="Solo para DESPIDO — fecha efectiva de cese"
    )
    documento_resolucion = models.FileField(
        upload_to='disciplinaria/resoluciones/%Y/%m/',
        blank=True, null=True, verbose_name="Documento Resolución"
    )

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR')

    # Trazabilidad
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='medidas_registradas'
    )
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='medidas_resueltas'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medida Disciplinaria"
        verbose_name_plural = "Medidas Disciplinarias"
        ordering = ['-fecha_hechos']
        indexes = [
            models.Index(fields=['personal', 'estado']),
            models.Index(fields=['-fecha_hechos']),
            models.Index(fields=['tipo_medida', 'estado']),
        ]

    def __str__(self):
        return f"{self.get_tipo_medida_display()} — {self.personal.apellidos_nombres} — {self.fecha_hechos}"

    def notificar(self):
        """Marca como notificada y calcula fecha límite de descargo."""
        self.estado = 'NOTIFICADA'
        if self.tipo_medida == 'DESPIDO' and self.fecha_carta_preaviso:
            # 6 días hábiles (Art. 31 DS 003-97-TR)
            self.fecha_limite_descargo = self._sumar_dias_habiles(self.fecha_carta_preaviso, 6)
            self.estado = 'EN_DESCARGO'
        self.save()

    def resolver(self, usuario, resolucion_texto):
        """Resuelve la medida disciplinaria."""
        self.estado = 'RESUELTA'
        self.resuelto_por = usuario
        self.fecha_resolucion = date.today()
        self.resolucion = resolucion_texto
        self.save()

    @property
    def dias_para_descargo(self):
        """Días restantes para presentar descargo."""
        if not self.fecha_limite_descargo:
            return None
        delta = (self.fecha_limite_descargo - date.today()).days
        return max(0, delta)

    @property
    def escalamiento_requerido(self):
        """Verifica si se requiere escalamiento (3+ amonestaciones escritas en 12 meses)."""
        hace_12_meses = date.today() - timedelta(days=365)
        count = MedidaDisciplinaria.objects.filter(
            personal=self.personal,
            tipo_medida='ESCRITA',
            estado='RESUELTA',
            fecha_hechos__gte=hace_12_meses,
        ).count()
        return count >= 3

    @staticmethod
    def _sumar_dias_habiles(fecha_inicio, dias):
        """Suma N días hábiles a una fecha (excluye sáb y dom)."""
        actual = fecha_inicio
        agregados = 0
        while agregados < dias:
            actual += timedelta(days=1)
            if actual.weekday() < 5:  # Lun-Vie
                agregados += 1
        return actual


class Descargo(models.Model):
    """Descargo presentado por el trabajador."""
    ESTADO_CHOICES = [
        ('PRESENTADO', 'Presentado'),
        ('EN_REVISION', 'En Revisión'),
        ('ACEPTADO', 'Aceptado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    medida = models.ForeignKey(
        MedidaDisciplinaria, on_delete=models.CASCADE,
        related_name='descargos', verbose_name="Medida Disciplinaria"
    )
    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='descargos'
    )

    fecha_presentacion = models.DateField(default=date.today, verbose_name="Fecha Presentación")
    texto = models.TextField(verbose_name="Texto del Descargo")
    archivos_adjuntos = models.FileField(
        upload_to='disciplinaria/descargos/%Y/%m/',
        blank=True, null=True, verbose_name="Adjuntos"
    )

    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PRESENTADO')
    evaluacion = models.TextField(
        blank=True, verbose_name="Evaluación",
        help_text="Análisis del descargo por parte de HR/Legal"
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='descargos_revisados'
    )
    fecha_revision = models.DateField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Descargo"
        verbose_name_plural = "Descargos"
        ordering = ['-fecha_presentacion']

    def __str__(self):
        return f"Descargo de {self.personal.apellidos_nombres} — {self.fecha_presentacion}"

    @property
    def presentado_a_tiempo(self):
        """Verifica si el descargo fue presentado dentro del plazo."""
        if self.medida.fecha_limite_descargo:
            return self.fecha_presentacion <= self.medida.fecha_limite_descargo
        return True
