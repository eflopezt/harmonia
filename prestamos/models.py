"""
Módulo de Préstamos al Personal.
Gestiona préstamos, adelantos de sueldo/gratificación, y descuentos en nómina.
Referencia: BUK, Odoo hr_loan — adaptado a legislación peruana.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from personal.models import Personal


class TipoPrestamo(models.Model):
    """
    Tipos de préstamo configurables.
    Ejemplos: Préstamo personal, Adelanto de sueldo, Adelanto de gratificación,
    Adelanto de vacaciones, Préstamo de emergencia.
    """
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.SlugField(max_length=30, unique=True)
    descripcion = models.TextField(blank=True)

    max_cuotas = models.PositiveSmallIntegerField(
        default=12,
        verbose_name="Máximo de Cuotas",
    )
    tasa_interes_mensual = models.DecimalField(
        max_digits=5, decimal_places=3, default=Decimal('0.000'),
        verbose_name="Tasa Interés Mensual (%)",
        help_text="0 = sin interés"
    )
    monto_maximo = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Monto Máximo",
        help_text="Vacío = sin límite"
    )
    requiere_aprobacion = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tipo de Préstamo"
        verbose_name_plural = "Tipos de Préstamo"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Prestamo(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('PENDIENTE', 'Pendiente Aprobación'),
        ('APROBADO', 'Aprobado'),
        ('EN_CURSO', 'En Curso'),
        ('PAGADO', 'Pagado'),
        ('CANCELADO', 'Cancelado'),
    ]

    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE,
        related_name='prestamos', verbose_name="Trabajador"
    )
    tipo = models.ForeignKey(
        TipoPrestamo, on_delete=models.PROTECT,
        related_name='prestamos', verbose_name="Tipo"
    )

    monto_solicitado = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
        verbose_name="Monto Solicitado"
    )
    monto_aprobado = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Monto Aprobado"
    )
    num_cuotas = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        verbose_name="N° Cuotas"
    )
    cuota_mensual = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Cuota Mensual"
    )
    tasa_interes = models.DecimalField(
        max_digits=5, decimal_places=3, default=Decimal('0.000'),
        verbose_name="Tasa Interés (%)"
    )

    fecha_solicitud = models.DateField(default=date.today, verbose_name="Fecha Solicitud")
    fecha_aprobacion = models.DateField(null=True, blank=True)
    fecha_primer_descuento = models.DateField(
        null=True, blank=True,
        verbose_name="Inicio Descuento",
        help_text="Período desde el cual se descuenta"
    )

    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='BORRADOR')
    motivo = models.TextField(blank=True, verbose_name="Motivo")
    observaciones = models.TextField(blank=True)

    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prestamos_registrados'
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prestamos_aprobados'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['personal', 'estado']),
            models.Index(fields=['-fecha_solicitud']),
        ]

    def __str__(self):
        return f"{self.tipo} — {self.personal.apellidos_nombres} — S/ {self.monto_solicitado}"

    @property
    def monto_efectivo(self):
        return self.monto_aprobado or self.monto_solicitado

    @property
    def saldo_pendiente(self):
        pagado = self.cuotas.filter(estado='PAGADO').aggregate(
            t=models.Sum('monto_pagado')
        )['t'] or Decimal('0.00')
        return self.monto_efectivo - pagado

    @property
    def cuotas_pagadas(self):
        return self.cuotas.filter(estado='PAGADO').count()

    @property
    def porcentaje_avance(self):
        if not self.num_cuotas:
            return 0
        return round((self.cuotas_pagadas / self.num_cuotas) * 100)

    def generar_cuotas(self):
        """Genera cuotas al aprobar. Última cuota ajusta residuo."""
        from dateutil.relativedelta import relativedelta

        monto = self.monto_efectivo
        cuota_base = (monto / self.num_cuotas).quantize(Decimal('0.01'))
        inicio = self.fecha_primer_descuento or date.today().replace(day=1)

        # Ensure inicio is a date object (puede llegar como str desde el form)
        if isinstance(inicio, str):
            from datetime import datetime
            inicio = datetime.strptime(inicio, '%Y-%m-%d').date()

        cuotas = []
        acumulado = Decimal('0.00')
        for i in range(self.num_cuotas):
            periodo = inicio + relativedelta(months=i)
            if i == self.num_cuotas - 1:
                monto_cuota = monto - acumulado
            else:
                monto_cuota = cuota_base
                acumulado += cuota_base
            cuotas.append(CuotaPrestamo(
                prestamo=self, numero=i + 1,
                periodo=periodo, monto=monto_cuota,
            ))

        CuotaPrestamo.objects.filter(prestamo=self).delete()
        CuotaPrestamo.objects.bulk_create(cuotas)
        self.cuota_mensual = cuota_base
        self.save(update_fields=['cuota_mensual'])

    def aprobar(self, usuario, monto_aprobado=None, fecha_descuento=None):
        self.estado = 'EN_CURSO'
        self.aprobado_por = usuario
        self.fecha_aprobacion = date.today()
        self.monto_aprobado = monto_aprobado or self.monto_solicitado
        self.tasa_interes = self.tipo.tasa_interes_mensual
        if fecha_descuento:
            # Asegurar tipo date
            if isinstance(fecha_descuento, str):
                from datetime import datetime
                fecha_descuento = datetime.strptime(fecha_descuento, '%Y-%m-%d').date()
            self.fecha_primer_descuento = fecha_descuento
        self.save()
        self.refresh_from_db()  # Garantizar tipos correctos
        self.generar_cuotas()


class CuotaPrestamo(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADO', 'Pagado'),
        ('PARCIAL', 'Pago Parcial'),
        ('CONDONADO', 'Condonado'),
    ]

    prestamo = models.ForeignKey(
        Prestamo, on_delete=models.CASCADE, related_name='cuotas'
    )
    numero = models.PositiveSmallIntegerField(verbose_name="N°")
    periodo = models.DateField(verbose_name="Período")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    monto_pagado = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PENDIENTE')
    fecha_pago = models.DateField(null=True, blank=True)
    referencia_nomina = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Cuota"
        verbose_name_plural = "Cuotas"
        ordering = ['prestamo', 'numero']
        unique_together = ['prestamo', 'numero']

    def __str__(self):
        return f"Cuota {self.numero}/{self.prestamo.num_cuotas} — S/ {self.monto}"

    def registrar_pago(self, monto=None, fecha=None, referencia=''):
        self.monto_pagado = monto or self.monto
        self.fecha_pago = fecha or date.today()
        self.referencia_nomina = referencia
        self.estado = 'PAGADO' if self.monto_pagado >= self.monto else 'PARCIAL'
        self.save()
        # Auto-cerrar préstamo si todas las cuotas están pagadas
        if not self.prestamo.cuotas.exclude(estado__in=['PAGADO', 'CONDONADO']).exists():
            self.prestamo.estado = 'PAGADO'
            self.prestamo.save(update_fields=['estado'])
