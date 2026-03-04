"""
Módulo de Capacitaciones / LMS Ligero.
Tracking de capacitaciones, certificaciones y cumplimiento obligatorio.

Referencia: Ley 29783 (SST), DS 005-2012-TR — capacitaciones SSOMA obligatorias.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from personal.models import Personal


class CategoriaCapacitacion(models.Model):
    """Categorías para agrupar capacitaciones."""
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.SlugField(max_length=30, unique=True)
    icono = models.CharField(max_length=50, default='fa-chalkboard-teacher')
    color = models.CharField(max_length=20, default='primary')
    orden = models.PositiveSmallIntegerField(default=10)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría de Capacitación"
        verbose_name_plural = "Categorías de Capacitación"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Capacitacion(models.Model):
    """Capacitación/curso registrado en el sistema."""
    TIPO_CHOICES = [
        ('INTERNA', 'Interna'),
        ('EXTERNA', 'Externa'),
        ('ELEARNING', 'E-Learning'),
        ('INDUCCION', 'Inducción'),
        ('SSOMA', 'SSOMA'),
    ]
    ESTADO_CHOICES = [
        ('PROGRAMADA', 'Programada'),
        ('EN_CURSO', 'En Curso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]

    titulo = models.CharField(max_length=255, verbose_name="Título")
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        CategoriaCapacitacion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='capacitaciones'
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default='INTERNA')

    # Logística
    instructor = models.CharField(max_length=200, blank=True, verbose_name="Instructor/Proveedor")
    lugar = models.CharField(max_length=200, blank=True, verbose_name="Lugar")
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha Fin")
    horas = models.DecimalField(
        max_digits=5, decimal_places=1,
        validators=[MinValueValidator(Decimal('0.5'))],
        verbose_name="Horas"
    )
    costo = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Costo (S/)"
    )

    # Participantes
    participantes = models.ManyToManyField(
        Personal, through='AsistenciaCapacitacion',
        related_name='capacitaciones_asignadas', blank=True,
    )
    max_participantes = models.PositiveSmallIntegerField(
        default=0, verbose_name="Máx. Participantes",
        help_text="0 = sin límite"
    )

    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='PROGRAMADA')
    obligatoria = models.BooleanField(
        default=False,
        help_text="Si es obligatoria, aparecerá como pendiente en incumplimientos"
    )
    material_url = models.URLField(blank=True, verbose_name="URL Material")
    material_archivo = models.FileField(
        upload_to='capacitaciones/material/%Y/%m/',
        blank=True, null=True, verbose_name="Material (archivo)"
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Capacitación"
        verbose_name_plural = "Capacitaciones"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['-fecha_inicio']),
            models.Index(fields=['estado', 'tipo']),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()}) — {self.fecha_inicio}"

    @property
    def num_inscritos(self):
        return self.asistencias.count()

    @property
    def num_aprobados(self):
        return self.asistencias.filter(aprobado=True).count()

    @property
    def tasa_aprobacion(self):
        total = self.num_inscritos
        if not total:
            return 0
        return round((self.num_aprobados / total) * 100)


class AsistenciaCapacitacion(models.Model):
    """Asistencia de un trabajador a una capacitación."""
    ESTADO_CHOICES = [
        ('INSCRITO', 'Inscrito'),
        ('ASISTIO', 'Asistió'),
        ('NO_ASISTIO', 'No Asistió'),
        ('PARCIAL', 'Asistencia Parcial'),
    ]

    capacitacion = models.ForeignKey(
        Capacitacion, on_delete=models.CASCADE,
        related_name='asistencias'
    )
    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='asistencias_capacitacion'
    )
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='INSCRITO')
    nota = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Nota/Calificación"
    )
    aprobado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    # Certificado
    certificado = models.FileField(
        upload_to='capacitaciones/certificados/%Y/%m/',
        blank=True, null=True, verbose_name="Certificado"
    )
    fecha_certificado = models.DateField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asistencia a Capacitación"
        verbose_name_plural = "Asistencias a Capacitaciones"
        unique_together = ['capacitacion', 'personal']
        ordering = ['personal__apellidos_nombres']

    def __str__(self):
        return f"{self.personal.apellidos_nombres} — {self.capacitacion.titulo}"


class RequerimientoCapacitacion(models.Model):
    """
    Requerimiento de capacitación por cargo/área.
    Permite definir qué capacitaciones son obligatorias para ciertos perfiles.
    """
    FRECUENCIA_CHOICES = [
        ('UNICA', 'Única vez'),
        ('ANUAL', 'Anual'),
        ('SEMESTRAL', 'Semestral'),
        ('TRIMESTRAL', 'Trimestral'),
    ]

    nombre = models.CharField(max_length=200, verbose_name="Nombre del Requerimiento")
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        CategoriaCapacitacion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requerimientos'
    )

    # A quién aplica
    aplica_todos = models.BooleanField(
        default=False, help_text="Aplica a todo el personal activo"
    )
    aplica_areas = models.ManyToManyField(
        'personal.Area', blank=True, related_name='requerimientos_capacitacion',
        verbose_name="Áreas Aplica"
    )
    aplica_staff = models.BooleanField(default=True)
    aplica_rco = models.BooleanField(default=True)

    frecuencia = models.CharField(max_length=12, choices=FRECUENCIA_CHOICES, default='ANUAL')
    horas_minimas = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal('1.0'),
        verbose_name="Horas Mínimas"
    )
    vigencia_dias = models.PositiveIntegerField(
        default=365, verbose_name="Vigencia (días)",
        help_text="Días de vigencia de la capacitación antes de requerir recertificación"
    )
    base_legal = models.CharField(max_length=200, blank=True)
    obligatorio = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Requerimiento de Capacitación"
        verbose_name_plural = "Requerimientos de Capacitación"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_frecuencia_display()})"


class CertificacionTrabajador(models.Model):
    """Certificación vigente de un trabajador (resultado de capacitación aprobada)."""
    ESTADO_CHOICES = [
        ('VIGENTE', 'Vigente'),
        ('POR_VENCER', 'Por Vencer'),
        ('VENCIDA', 'Vencida'),
        ('REVOCADA', 'Revocada'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='certificaciones'
    )
    requerimiento = models.ForeignKey(
        RequerimientoCapacitacion, on_delete=models.CASCADE,
        related_name='certificaciones'
    )
    capacitacion = models.ForeignKey(
        Capacitacion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='certificaciones_generadas',
        help_text="Capacitación que generó esta certificación"
    )

    fecha_obtencion = models.DateField(verbose_name="Fecha Obtención")
    fecha_vencimiento = models.DateField(
        null=True, blank=True, verbose_name="Fecha Vencimiento"
    )
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='VIGENTE')
    archivo = models.FileField(
        upload_to='capacitaciones/certs/%Y/%m/',
        blank=True, null=True, verbose_name="Certificado"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Certificación del Trabajador"
        verbose_name_plural = "Certificaciones de Trabajadores"
        ordering = ['-fecha_obtencion']
        indexes = [
            models.Index(fields=['personal', 'estado']),
            models.Index(fields=['fecha_vencimiento']),
        ]

    def __str__(self):
        return f"{self.requerimiento.nombre} — {self.personal.apellidos_nombres}"

    def save(self, *args, **kwargs):
        # Auto-calcular vencimiento si no se especifica
        if not self.fecha_vencimiento and self.requerimiento.vigencia_dias:
            self.fecha_vencimiento = self.fecha_obtencion + timedelta(days=self.requerimiento.vigencia_dias)
        # Auto-calcular estado
        if self.fecha_vencimiento:
            hoy = date.today()
            if self.fecha_vencimiento < hoy:
                self.estado = 'VENCIDA'
            elif self.fecha_vencimiento <= hoy + timedelta(days=30):
                self.estado = 'POR_VENCER'
            else:
                self.estado = 'VIGENTE'
        super().save(*args, **kwargs)
