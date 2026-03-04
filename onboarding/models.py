"""
Módulo de Onboarding y Offboarding.
Gestiona procesos de incorporación y desvinculación de personal,
con plantillas configurables y checklist de pasos por responsable.
"""
from datetime import date, timedelta

from django.conf import settings
from django.db import models

from personal.models import Personal, Area


# ══════════════════════════════════════════════════════════════
# ONBOARDING — PLANTILLAS
# ══════════════════════════════════════════════════════════════

class PlantillaOnboarding(models.Model):
    """Plantilla reutilizable para procesos de onboarding."""
    GRUPO_CHOICES = [
        ('STAFF', 'STAFF'),
        ('RCO', 'RCO'),
        ('TODOS', 'Todos'),
    ]

    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    aplica_grupo = models.CharField(
        max_length=10, choices=GRUPO_CHOICES, default='TODOS',
        verbose_name="Aplica a Grupo",
        help_text="Grupo de tareo al que aplica esta plantilla"
    )
    aplica_areas = models.ManyToManyField(
        Area, blank=True, related_name='plantillas_onboarding',
        verbose_name="Aplica a Áreas",
        help_text="Dejar vacío para aplicar a todas las áreas"
    )
    activa = models.BooleanField(default=True, verbose_name="Activa")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plantilla de Onboarding"
        verbose_name_plural = "Plantillas de Onboarding"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def total_pasos(self):
        return self.pasos.count()


class PasoPlantilla(models.Model):
    """Paso dentro de una plantilla de onboarding."""
    TIPO_CHOICES = [
        ('TAREA', 'Tarea'),
        ('DOCUMENTO', 'Documento'),
        ('CAPACITACION', 'Capacitación'),
        ('NOTIFICACION', 'Notificación'),
        ('APROBACION', 'Aprobación'),
    ]
    RESPONSABLE_CHOICES = [
        ('RRHH', 'RRHH'),
        ('JEFE', 'Jefe Directo'),
        ('TI', 'TI / Sistemas'),
        ('TRABAJADOR', 'Trabajador'),
    ]

    plantilla = models.ForeignKey(
        PlantillaOnboarding, on_delete=models.CASCADE,
        related_name='pasos', verbose_name="Plantilla"
    )
    orden = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    titulo = models.CharField(max_length=300, verbose_name="Título")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    tipo = models.CharField(
        max_length=15, choices=TIPO_CHOICES, default='TAREA',
        verbose_name="Tipo"
    )
    responsable_tipo = models.CharField(
        max_length=15, choices=RESPONSABLE_CHOICES, default='RRHH',
        verbose_name="Responsable"
    )
    dias_plazo = models.PositiveSmallIntegerField(
        default=1, verbose_name="Días de Plazo",
        help_text="Días calendario para completar este paso desde la fecha de ingreso"
    )
    obligatorio = models.BooleanField(default=True, verbose_name="Obligatorio")

    class Meta:
        verbose_name = "Paso de Plantilla Onboarding"
        verbose_name_plural = "Pasos de Plantilla Onboarding"
        ordering = ['plantilla', 'orden']
        unique_together = ['plantilla', 'orden']

    def __str__(self):
        return f"{self.orden}. {self.titulo}"


# ══════════════════════════════════════════════════════════════
# ONBOARDING — PROCESOS
# ══════════════════════════════════════════════════════════════

class ProcesoOnboarding(models.Model):
    """Proceso de onboarding activo para un trabajador."""
    ESTADO_CHOICES = [
        ('EN_CURSO', 'En Curso'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='procesos_onboarding', verbose_name="Trabajador"
    )
    plantilla = models.ForeignKey(
        PlantillaOnboarding, on_delete=models.PROTECT,
        related_name='procesos', verbose_name="Plantilla"
    )
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    fecha_inicio = models.DateField(
        default=date.today, verbose_name="Fecha de Inicio del Proceso"
    )
    estado = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default='EN_CURSO',
        verbose_name="Estado"
    )
    iniciado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='onboardings_iniciados',
        verbose_name="Iniciado por"
    )
    notas = models.TextField(blank=True, verbose_name="Notas")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proceso de Onboarding"
        verbose_name_plural = "Procesos de Onboarding"
        ordering = ['-creado_en']

    def __str__(self):
        return f"Onboarding: {self.personal.apellidos_nombres}"

    @property
    def total_pasos(self):
        return self.pasos.count()

    @property
    def pasos_completados(self):
        return self.pasos.filter(estado='COMPLETADO').count()

    @property
    def porcentaje_avance(self):
        total = self.total_pasos
        if total == 0:
            return 0
        return round(self.pasos_completados * 100 / total)

    @property
    def dias_transcurridos(self):
        return (date.today() - self.fecha_inicio).days


class PasoOnboarding(models.Model):
    """Paso concreto de un proceso de onboarding."""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROGRESO', 'En Progreso'),
        ('COMPLETADO', 'Completado'),
        ('OMITIDO', 'Omitido'),
    ]

    proceso = models.ForeignKey(
        ProcesoOnboarding, on_delete=models.CASCADE,
        related_name='pasos', verbose_name="Proceso"
    )
    paso_plantilla = models.ForeignKey(
        PasoPlantilla, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='instancias',
        verbose_name="Paso Plantilla"
    )
    orden = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    titulo = models.CharField(max_length=300, verbose_name="Título")
    estado = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default='PENDIENTE',
        verbose_name="Estado"
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pasos_onboarding_asignados',
        verbose_name="Responsable"
    )
    fecha_limite = models.DateField(
        null=True, blank=True, verbose_name="Fecha Límite"
    )
    fecha_completado = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha Completado"
    )
    completado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pasos_onboarding_completados',
        verbose_name="Completado por"
    )
    comentarios = models.TextField(blank=True, verbose_name="Comentarios")

    class Meta:
        verbose_name = "Paso de Onboarding"
        verbose_name_plural = "Pasos de Onboarding"
        ordering = ['proceso', 'orden']

    def __str__(self):
        return f"{self.orden}. {self.titulo} ({self.get_estado_display()})"

    @property
    def esta_vencido(self):
        if self.estado in ('COMPLETADO', 'OMITIDO'):
            return False
        if self.fecha_limite and date.today() > self.fecha_limite:
            return True
        return False


# ══════════════════════════════════════════════════════════════
# OFFBOARDING — PLANTILLAS
# ══════════════════════════════════════════════════════════════

class PlantillaOffboarding(models.Model):
    """Plantilla reutilizable para procesos de offboarding."""
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activa = models.BooleanField(default=True, verbose_name="Activa")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plantilla de Offboarding"
        verbose_name_plural = "Plantillas de Offboarding"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def total_pasos(self):
        return self.pasos.count()


class PasoPlantillaOff(models.Model):
    """Paso dentro de una plantilla de offboarding."""
    TIPO_CHOICES = PasoPlantilla.TIPO_CHOICES
    RESPONSABLE_CHOICES = PasoPlantilla.RESPONSABLE_CHOICES

    plantilla = models.ForeignKey(
        PlantillaOffboarding, on_delete=models.CASCADE,
        related_name='pasos', verbose_name="Plantilla"
    )
    orden = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    titulo = models.CharField(max_length=300, verbose_name="Título")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    tipo = models.CharField(
        max_length=15, choices=TIPO_CHOICES, default='TAREA',
        verbose_name="Tipo"
    )
    responsable_tipo = models.CharField(
        max_length=15, choices=RESPONSABLE_CHOICES, default='RRHH',
        verbose_name="Responsable"
    )
    dias_plazo = models.PositiveSmallIntegerField(
        default=1, verbose_name="Días de Plazo",
        help_text="Días calendario para completar este paso desde la fecha de cese"
    )
    obligatorio = models.BooleanField(default=True, verbose_name="Obligatorio")

    class Meta:
        verbose_name = "Paso de Plantilla Offboarding"
        verbose_name_plural = "Pasos de Plantilla Offboarding"
        ordering = ['plantilla', 'orden']
        unique_together = ['plantilla', 'orden']

    def __str__(self):
        return f"{self.orden}. {self.titulo}"


# ══════════════════════════════════════════════════════════════
# OFFBOARDING — PROCESOS
# ══════════════════════════════════════════════════════════════

class ProcesoOffboarding(models.Model):
    """Proceso de offboarding activo para un trabajador."""
    ESTADO_CHOICES = ProcesoOnboarding.ESTADO_CHOICES
    MOTIVO_CHOICES = [
        ('RENUNCIA', 'Renuncia Voluntaria'),
        ('DESPIDO', 'Despido'),
        ('MUTUO_ACUERDO', 'Mutuo Acuerdo'),
        ('FIN_CONTRATO', 'Fin de Contrato'),
        ('JUBILACION', 'Jubilación'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='procesos_offboarding', verbose_name="Trabajador"
    )
    plantilla = models.ForeignKey(
        PlantillaOffboarding, on_delete=models.PROTECT,
        related_name='procesos', verbose_name="Plantilla"
    )
    fecha_cese = models.DateField(verbose_name="Fecha de Cese")
    motivo_cese = models.CharField(
        max_length=15, choices=MOTIVO_CHOICES,
        verbose_name="Motivo de Cese"
    )
    estado = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default='EN_CURSO',
        verbose_name="Estado"
    )
    iniciado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='offboardings_iniciados',
        verbose_name="Iniciado por"
    )
    notas = models.TextField(blank=True, verbose_name="Notas")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proceso de Offboarding"
        verbose_name_plural = "Procesos de Offboarding"
        ordering = ['-creado_en']

    def __str__(self):
        return f"Offboarding: {self.personal.apellidos_nombres}"

    @property
    def total_pasos(self):
        return self.pasos.count()

    @property
    def pasos_completados(self):
        return self.pasos.filter(estado='COMPLETADO').count()

    @property
    def porcentaje_avance(self):
        total = self.total_pasos
        if total == 0:
            return 0
        return round(self.pasos_completados * 100 / total)

    @property
    def dias_transcurridos(self):
        return (date.today() - self.creado_en.date()).days


class PasoOffboarding(models.Model):
    """Paso concreto de un proceso de offboarding."""
    ESTADO_CHOICES = PasoOnboarding.ESTADO_CHOICES

    proceso = models.ForeignKey(
        ProcesoOffboarding, on_delete=models.CASCADE,
        related_name='pasos', verbose_name="Proceso"
    )
    paso_plantilla = models.ForeignKey(
        PasoPlantillaOff, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='instancias',
        verbose_name="Paso Plantilla"
    )
    orden = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    titulo = models.CharField(max_length=300, verbose_name="Título")
    estado = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default='PENDIENTE',
        verbose_name="Estado"
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pasos_offboarding_asignados',
        verbose_name="Responsable"
    )
    fecha_limite = models.DateField(
        null=True, blank=True, verbose_name="Fecha Límite"
    )
    fecha_completado = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha Completado"
    )
    completado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pasos_offboarding_completados',
        verbose_name="Completado por"
    )
    comentarios = models.TextField(blank=True, verbose_name="Comentarios")

    class Meta:
        verbose_name = "Paso de Offboarding"
        verbose_name_plural = "Pasos de Offboarding"
        ordering = ['proceso', 'orden']

    def __str__(self):
        return f"{self.orden}. {self.titulo} ({self.get_estado_display()})"

    @property
    def esta_vencido(self):
        if self.estado in ('COMPLETADO', 'OMITIDO'):
            return False
        if self.fecha_limite and date.today() > self.fecha_limite:
            return True
        return False
