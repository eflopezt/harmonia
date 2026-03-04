"""
Módulo de Viáticos y Condiciones de Trabajo (CDT).
Gestiona adelantos, rendiciones y conciliación de viáticos del personal foráneo.
Referencia: BUK, Odoo hr_expense — adaptado a legislación peruana (Art. 37° LIR).
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from personal.models import Personal


class ConceptoViatico(models.Model):
    """Conceptos de gasto para viáticos (alimentación, hospedaje, movilidad, etc.)."""
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.SlugField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)
    tope_diario = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        verbose_name="Tope Diario (S/)",
        help_text="Monto máximo diario para este concepto. Vacío = sin tope."
    )
    requiere_comprobante = models.BooleanField(
        default=True,
        help_text="Si requiere boleta/factura para la rendición"
    )
    afecto_renta = models.BooleanField(
        default=False,
        help_text="Si el exceso del tope es afecto a renta de 5ta categoría"
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=10)

    class Meta:
        verbose_name = "Concepto de Viático"
        verbose_name_plural = "Conceptos de Viático"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class AsignacionViatico(models.Model):
    """
    Asignación mensual de viáticos a un trabajador.
    Representa el adelanto que se da al personal foráneo para cubrir CDT.
    """
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('APROBADO', 'Aprobado'),
        ('ENTREGADO', 'Entregado'),
        ('EN_RENDICION', 'En Rendición'),
        ('CONCILIADO', 'Conciliado'),
        ('CANCELADO', 'Cancelado'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='asignaciones_viatico', verbose_name="Trabajador"
    )
    periodo = models.DateField(
        verbose_name="Período",
        help_text="Primer día del mes al que corresponde la asignación"
    )
    monto_asignado = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
        verbose_name="Monto Asignado"
    )
    monto_adicional = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Monto Adicional",
        help_text="Reembolsos o ajustes al monto base"
    )

    # Ubicación / proyecto
    ubicacion = models.CharField(
        max_length=150, blank=True,
        verbose_name="Ubicación/Proyecto",
        help_text="Lugar de destino del trabajador"
    )
    dias_campo = models.PositiveSmallIntegerField(
        default=0, verbose_name="Días en Campo",
        help_text="Días efectivos en campo para el período"
    )

    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='BORRADOR')
    fecha_entrega = models.DateField(null=True, blank=True, verbose_name="Fecha Entrega")
    observaciones = models.TextField(blank=True)

    # Conciliación
    monto_rendido = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Monto Rendido"
    )
    monto_devuelto = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Monto Devuelto",
        help_text="Monto que el trabajador devuelve a la empresa"
    )
    monto_reembolso = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Monto a Reembolsar",
        help_text="Monto que la empresa reembolsa al trabajador"
    )
    fecha_conciliacion = models.DateField(null=True, blank=True)

    # Trazabilidad
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='viaticos_creados'
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='viaticos_aprobados'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asignación de Viático"
        verbose_name_plural = "Asignaciones de Viáticos"
        ordering = ['-periodo', 'personal__apellidos_nombres']
        unique_together = ['personal', 'periodo']
        indexes = [
            models.Index(fields=['personal', 'estado']),
            models.Index(fields=['-periodo']),
        ]

    def __str__(self):
        return f"{self.personal.apellidos_nombres} — {self.periodo.strftime('%m/%Y')} — S/ {self.monto_total}"

    @property
    def monto_total(self):
        """Monto total asignado (base + adicional)."""
        return self.monto_asignado + self.monto_adicional

    @property
    def saldo(self):
        """Saldo: positivo = trabajador gastó de más, negativo = sobra dinero."""
        return self.monto_rendido - self.monto_total

    @property
    def estado_conciliacion(self):
        """Resumen de conciliación."""
        diff = self.saldo
        if diff == 0:
            return 'CUADRADO'
        elif diff > 0:
            return 'REEMBOLSAR'  # La empresa debe al trabajador
        else:
            return 'DEVOLVER'  # El trabajador debe a la empresa

    def aprobar(self, usuario):
        """Aprueba la asignación."""
        self.estado = 'APROBADO'
        self.aprobado_por = usuario
        self.save(update_fields=['estado', 'aprobado_por'])

    def entregar(self, fecha=None):
        """Marca la asignación como entregada al trabajador."""
        self.estado = 'ENTREGADO'
        self.fecha_entrega = fecha or date.today()
        self.save(update_fields=['estado', 'fecha_entrega'])

    def conciliar(self):
        """Concilia la asignación con los gastos rendidos."""
        total_gastos = self.gastos.filter(
            estado='APROBADO'
        ).aggregate(t=models.Sum('monto'))['t'] or Decimal('0.00')

        self.monto_rendido = total_gastos
        diff = self.saldo

        if diff > 0:
            self.monto_reembolso = diff
            self.monto_devuelto = Decimal('0.00')
        elif diff < 0:
            self.monto_devuelto = abs(diff)
            self.monto_reembolso = Decimal('0.00')
        else:
            self.monto_devuelto = Decimal('0.00')
            self.monto_reembolso = Decimal('0.00')

        self.estado = 'CONCILIADO'
        self.fecha_conciliacion = date.today()
        self.save()


class GastoViatico(models.Model):
    """
    Gasto individual dentro de una rendición de viáticos.
    Cada registro es un comprobante o gasto del trabajador.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('OBSERVADO', 'Observado'),
    ]

    TIPO_COMPROBANTE_CHOICES = [
        ('BOLETA', 'Boleta de Venta'),
        ('FACTURA', 'Factura'),
        ('RECIBO', 'Recibo por Honorarios'),
        ('TICKET', 'Ticket / Voucher'),
        ('DECLARACION', 'Declaración Jurada'),
        ('OTRO', 'Otro'),
    ]

    asignacion = models.ForeignKey(
        AsignacionViatico, on_delete=models.CASCADE,
        related_name='gastos', verbose_name="Asignación"
    )
    concepto = models.ForeignKey(
        ConceptoViatico, on_delete=models.PROTECT,
        related_name='gastos', verbose_name="Concepto"
    )

    fecha_gasto = models.DateField(verbose_name="Fecha del Gasto")
    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Monto (S/)"
    )
    descripcion = models.CharField(max_length=255, blank=True, verbose_name="Descripción")

    # Comprobante
    tipo_comprobante = models.CharField(
        max_length=15, choices=TIPO_COMPROBANTE_CHOICES,
        default='BOLETA', verbose_name="Tipo Comprobante"
    )
    numero_comprobante = models.CharField(
        max_length=50, blank=True, verbose_name="N° Comprobante"
    )
    ruc_proveedor = models.CharField(
        max_length=11, blank=True, verbose_name="RUC Proveedor"
    )
    archivo_comprobante = models.FileField(
        upload_to='viaticos/comprobantes/%Y/%m/',
        blank=True, null=True,
        verbose_name="Archivo Comprobante"
    )

    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='PENDIENTE')
    motivo_rechazo = models.TextField(blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gasto de Viático"
        verbose_name_plural = "Gastos de Viáticos"
        ordering = ['-fecha_gasto']
        indexes = [
            models.Index(fields=['asignacion', 'estado']),
        ]

    def __str__(self):
        return f"{self.concepto.nombre} — S/ {self.monto} — {self.fecha_gasto}"

    @property
    def excede_tope(self):
        """Verifica si el gasto excede el tope diario del concepto."""
        if not self.concepto.tope_diario:
            return False
        return self.monto > self.concepto.tope_diario

    @property
    def monto_exceso(self):
        """Monto que excede el tope diario (afecto a renta si aplica)."""
        if not self.concepto.tope_diario:
            return Decimal('0.00')
        exceso = self.monto - self.concepto.tope_diario
        return max(exceso, Decimal('0.00'))
