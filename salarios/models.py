"""
Módulo de Estructura Salarial.
Gestiona bandas salariales, historial de remuneraciones y simulaciones de incremento.

Reglas de negocio:
- Moneda por defecto: PEN (Sol peruano)
- Compa-ratio = remuneración actual / medio de banda (mide equidad salarial)
- Las bandas salariales definen rangos por cargo y nivel
- Las simulaciones permiten propuestas masivas de incremento antes de aplicar
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from personal.models import Personal


class BandaSalarial(models.Model):
    """Banda salarial por cargo y nivel jerárquico."""
    NIVEL_CHOICES = [
        ('JUNIOR', 'Junior'),
        ('SEMI_SENIOR', 'Semi Senior'),
        ('SENIOR', 'Senior'),
        ('LEAD', 'Lead'),
        ('GERENTE', 'Gerente'),
    ]
    MONEDA_CHOICES = [
        ('PEN', 'Sol (S/)'),
        ('USD', 'Dólar (US$)'),
    ]

    cargo = models.CharField(max_length=150, verbose_name="Cargo")
    nivel = models.CharField(
        max_length=12, choices=NIVEL_CHOICES,
        verbose_name="Nivel"
    )
    minimo = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Mínimo",
        help_text="Límite inferior de la banda salarial"
    )
    medio = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Medio (Midpoint)",
        help_text="Punto medio de referencia para compa-ratio"
    )
    maximo = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Máximo",
        help_text="Límite superior de la banda salarial"
    )
    moneda = models.CharField(
        max_length=3, choices=MONEDA_CHOICES,
        default='PEN', verbose_name="Moneda"
    )
    activa = models.BooleanField(default=True, verbose_name="Activa")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Banda Salarial"
        verbose_name_plural = "Bandas Salariales"
        ordering = ['cargo', 'nivel']
        unique_together = ['cargo', 'nivel']
        indexes = [
            models.Index(fields=['cargo', 'nivel']),
            models.Index(fields=['activa']),
        ]

    def __str__(self):
        return f"{self.cargo} — {self.get_nivel_display()} ({self.moneda} {self.minimo}–{self.maximo})"

    @property
    def amplitud(self):
        """Amplitud de la banda: (máximo - mínimo) / mínimo * 100."""
        if self.minimo and self.minimo > 0:
            return round((self.maximo - self.minimo) / self.minimo * 100, 1)
        return Decimal('0')

    def compa_ratio(self, remuneracion):
        """Calcula el compa-ratio: remuneración / midpoint de la banda."""
        if self.medio and self.medio > 0:
            return round(remuneracion / self.medio, 3)
        return Decimal('0')

    def posicion_en_banda(self, remuneracion):
        """Posición relativa dentro de la banda (0% = mín, 100% = máx)."""
        rango = self.maximo - self.minimo
        if rango > 0:
            return round((remuneracion - self.minimo) / rango * 100, 1)
        return Decimal('0')


class HistorialSalarial(models.Model):
    """Registro de cada cambio salarial de un trabajador."""
    MOTIVO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('INCREMENTO', 'Incremento Anual'),
        ('PROMOCION', 'Promoción'),
        ('AJUSTE', 'Ajuste de Mercado'),
        ('REVALORACION', 'Revalorización'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='historial_salarial', verbose_name="Trabajador"
    )
    fecha_efectiva = models.DateField(verbose_name="Fecha Efectiva")
    remuneracion_anterior = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Remuneración Anterior",
        help_text="Sueldo base antes del cambio"
    )
    remuneracion_nueva = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Remuneración Nueva",
        help_text="Sueldo base después del cambio"
    )
    motivo = models.CharField(
        max_length=15, choices=MOTIVO_CHOICES,
        verbose_name="Motivo"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incrementos_aprobados',
        verbose_name="Aprobado por"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Historial Salarial"
        verbose_name_plural = "Historial Salarial"
        ordering = ['-fecha_efectiva']
        indexes = [
            models.Index(fields=['personal', '-fecha_efectiva']),
            models.Index(fields=['-fecha_efectiva']),
            models.Index(fields=['motivo']),
        ]

    def __str__(self):
        return (
            f"{self.personal.apellidos_nombres} — {self.get_motivo_display()} "
            f"({self.fecha_efectiva})"
        )

    @property
    def porcentaje_incremento(self):
        """Calcula el porcentaje de incremento respecto a la remuneración anterior."""
        if self.remuneracion_anterior and self.remuneracion_anterior > 0:
            return round(
                (self.remuneracion_nueva - self.remuneracion_anterior)
                / self.remuneracion_anterior * 100, 2
            )
        return Decimal('0')

    @property
    def diferencia(self):
        """Diferencia absoluta entre remuneración nueva y anterior."""
        return self.remuneracion_nueva - self.remuneracion_anterior


class SimulacionIncremento(models.Model):
    """Simulación masiva de incrementos salariales antes de aplicar."""
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('APROBADA', 'Aprobada'),
        ('APLICADA', 'Aplicada'),
    ]
    TIPO_CHOICES = [
        ('PORCENTAJE', 'Porcentaje'),
        ('MONTO_FIJO', 'Monto Fijo'),
    ]

    nombre = models.CharField(max_length=200, verbose_name="Nombre de la Simulación")
    fecha = models.DateField(verbose_name="Fecha de Simulación")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES,
        default='BORRADOR', verbose_name="Estado"
    )
    tipo = models.CharField(
        max_length=12, choices=TIPO_CHOICES,
        default='PORCENTAJE', verbose_name="Tipo de Incremento"
    )
    presupuesto_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Presupuesto Total",
        help_text="Presupuesto máximo disponible para esta simulación"
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='simulaciones_creadas',
        verbose_name="Creado por"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Simulación de Incremento"
        verbose_name_plural = "Simulaciones de Incremento"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f"{self.nombre} — {self.fecha} ({self.get_estado_display()})"

    @property
    def total_empleados(self):
        """Cantidad de empleados incluidos en la simulación."""
        return self.detalles.count()

    @property
    def costo_total(self):
        """Costo mensual total de los incrementos propuestos."""
        from django.db.models import Sum
        result = self.detalles.filter(aprobado=True).aggregate(
            total=Sum('incremento_propuesto')
        )
        return result['total'] or Decimal('0')

    @property
    def costo_anual(self):
        """Costo anual proyectado (costo mensual * 12)."""
        return self.costo_total * 12

    @property
    def dentro_presupuesto(self):
        """Indica si el costo anual no excede el presupuesto total."""
        if self.presupuesto_total:
            return self.costo_anual <= self.presupuesto_total
        return True


class DetalleSimulacion(models.Model):
    """Detalle de incremento propuesto para un trabajador dentro de una simulación."""
    simulacion = models.ForeignKey(
        SimulacionIncremento, on_delete=models.CASCADE,
        related_name='detalles', verbose_name="Simulación"
    )
    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='simulaciones_detalle', verbose_name="Trabajador"
    )
    remuneracion_actual = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Remuneración Actual"
    )
    incremento_propuesto = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Incremento Propuesto",
        help_text="Monto del incremento (no el nuevo sueldo)"
    )
    aprobado = models.BooleanField(
        default=True, verbose_name="Aprobado",
        help_text="Marcar si este incremento individual fue aprobado"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Detalle de Simulación"
        verbose_name_plural = "Detalles de Simulación"
        ordering = ['personal__apellidos_nombres']
        unique_together = ['simulacion', 'personal']
        indexes = [
            models.Index(fields=['simulacion', 'personal']),
            models.Index(fields=['aprobado']),
        ]

    def __str__(self):
        return f"{self.personal.apellidos_nombres} — +{self.incremento_propuesto}"

    @property
    def remuneracion_nueva(self):
        """Remuneración nueva = actual + incremento propuesto."""
        return self.remuneracion_actual + self.incremento_propuesto

    @property
    def porcentaje_incremento(self):
        """Porcentaje de incremento respecto a la remuneración actual."""
        if self.remuneracion_actual and self.remuneracion_actual > 0:
            return round(
                self.incremento_propuesto / self.remuneracion_actual * 100, 2
            )
        return Decimal('0')
