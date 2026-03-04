"""
Cierre Mensual — Modelos.

PeriodoCierre: representa un período (anio/mes) con su estado de cierre.
PasoCierre:    cada verificación/acción del wizard de cierre.
"""
from django.db import models
from django.utils import timezone


class PeriodoCierre(models.Model):
    ESTADO_CHOICES = [
        ('ABIERTO',    'Abierto — datos en edición'),
        ('EN_CIERRE',  'En Cierre — wizard en progreso'),
        ('CERRADO',    'Cerrado — período bloqueado'),
        ('REABIERTO',  'Reabierto — revisión post-cierre'),
    ]

    anio = models.PositiveSmallIntegerField(verbose_name='Año')
    mes  = models.PositiveSmallIntegerField(verbose_name='Mes')
    estado = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default='ABIERTO',
        verbose_name='Estado',
    )
    creado_en    = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    cerrado_en   = models.DateTimeField(null=True, blank=True)
    notas        = models.TextField(blank=True)

    class Meta:
        unique_together = [('anio', 'mes')]
        ordering = ['-anio', '-mes']
        verbose_name = 'Período de Cierre'
        verbose_name_plural = 'Períodos de Cierre'

    def __str__(self):
        MESES = ['Ene','Feb','Mar','Abr','May','Jun',
                 'Jul','Ago','Sep','Oct','Nov','Dic']
        return f'{MESES[self.mes - 1]} {self.anio} [{self.get_estado_display()}]'

    @property
    def mes_nombre(self):
        MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                 'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
        return MESES[self.mes - 1]

    @property
    def esta_cerrado(self):
        return self.estado == 'CERRADO'

    @property
    def pasos_completados(self):
        return self.pasos.filter(estado='OK').count()

    @property
    def total_pasos(self):
        return self.pasos.count()

    @property
    def porcentaje_avance(self):
        total = self.total_pasos
        return round(self.pasos_completados / total * 100) if total else 0


class PasoCierre(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE',  'Pendiente'),
        ('EJECUTANDO', 'Ejecutando...'),
        ('OK',         'Completado'),
        ('ERROR',      'Error'),
        ('ADVERTENCIA','Advertencia'),
        ('OMITIDO',    'Omitido'),
    ]

    # Códigos internos fijos para lógica de negocio
    CODIGO_CHOICES = [
        ('VERIFICAR_IMPORTACIONES', 'Verificar importaciones del período'),
        ('VALIDAR_DNI',             'Validar registros sin match de DNI'),
        ('VERIFICAR_SS',            'Verificar consistencia Sin Salida'),
        ('ASEGURAR_BANCO',          'Asegurar BancoHoras STAFF activo'),
        ('GENERAR_CARGA_S10',       'Generar Carga S10 para RCO'),
        ('REPORTE_CIERRE',          'Generar reporte de cierre'),
        ('BLOQUEAR_PERIODO',        'Bloquear período'),
    ]

    periodo   = models.ForeignKey(
        PeriodoCierre, on_delete=models.CASCADE, related_name='pasos',
    )
    codigo    = models.CharField(max_length=40, choices=CODIGO_CHOICES)
    orden     = models.PositiveSmallIntegerField()
    estado    = models.CharField(
        max_length=12, choices=ESTADO_CHOICES, default='PENDIENTE',
    )
    resultado = models.JSONField(default=dict, blank=True)
    ejecutado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['orden']
        unique_together = [('periodo', 'codigo')]
        verbose_name = 'Paso de Cierre'
        verbose_name_plural = 'Pasos de Cierre'

    def __str__(self):
        return f'{self.periodo} — Paso {self.orden}: {self.get_codigo_display()}'

    @property
    def icono(self):
        return {
            'PENDIENTE':   'fas fa-circle text-muted',
            'EJECUTANDO':  'fas fa-spinner fa-spin text-warning',
            'OK':          'fas fa-check-circle text-success',
            'ERROR':       'fas fa-times-circle text-danger',
            'ADVERTENCIA': 'fas fa-exclamation-circle text-warning',
            'OMITIDO':     'fas fa-minus-circle text-secondary',
        }.get(self.estado, 'fas fa-circle text-muted')

    @property
    def badge_class(self):
        return {
            'PENDIENTE':   'bg-secondary',
            'EJECUTANDO':  'bg-warning text-dark',
            'OK':          'bg-success',
            'ERROR':       'bg-danger',
            'ADVERTENCIA': 'bg-warning text-dark',
            'OMITIDO':     'bg-secondary',
        }.get(self.estado, 'bg-secondary')
