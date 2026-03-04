"""
Integraciones Perú — Modelos.

Registra el historial de exportaciones hacia sistemas externos:
T-Registro SUNAT, PLAME, AFPNet, bancos, ESSALUD y publicacion de vacantes.
"""
from django.conf import settings
from django.db import models


class LogExportacion(models.Model):
    """Registro de cada exportación de archivo hacia sistema externo."""

    TIPO_CHOICES = [
        ('T_REGISTRO_ALTA', 'T-Registro — Altas'),
        ('T_REGISTRO_BAJA', 'T-Registro — Bajas'),
        ('T_REGISTRO_MODIF', 'T-Registro — Modificaciones'),
        ('PLAME', 'PDT PLAME'),
        ('AFP_NET', 'AFP Net — Aportes'),
        ('BANCO_BCP', 'Banco BCP — Telecrédito'),
        ('BANCO_BBVA', 'Banco BBVA — Pagos'),
        ('BANCO_IBK', 'Banco Interbank — Pagos'),
        ('BANCO_SCO', 'Banco Scotiabank — Pagos'),
        ('BANCO_NACION', 'Banco de la Nación — Pagos'),
        ('ESSALUD', 'ESSALUD — Declaración'),
        ('PLANILLA_EXCEL', 'Planilla Excel resumen'),
        # Contabilidad
        ('CONCAR', 'Asiento CONCAR'),
        ('SIGO', 'Asiento SIGO / Softpyme'),
        ('SAP_EXCEL', 'Asiento SAP Excel (BAPI FB50)'),
        ('SIRE_PLE', 'SIRE PLE 5.1 — Libro Diario'),
        ('OTRO', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('OK', 'Exitoso'),
        ('ERROR', 'Error'),
        ('PARCIAL', 'Parcial'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    periodo = models.CharField(
        max_length=7, blank=True,
        help_text='Período en formato YYYY-MM (ej: 2026-03)',
    )
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='OK')
    registros = models.PositiveIntegerField(default=0, help_text='Cantidad de registros exportados')
    nombre_archivo = models.CharField(max_length=200, blank=True)
    notas = models.TextField(blank=True)

    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generado_en']
        verbose_name = 'Log de Exportación'
        verbose_name_plural = 'Logs de Exportación'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.periodo} ({self.registros} reg.)'


# ══════════════════════════════════════════════════════════════
# LOG PUBLICACION VACANTE
# ══════════════════════════════════════════════════════════════

class LogPublicacionVacante(models.Model):
    """
    Registro de cada intento de publicacion de una vacante en plataformas externas.

    Plataformas soportadas:
        - COMPUTRABAJO: export XML/JSON para feed masivo Computrabajo Peru
        - BUMERAN:      export XML/JSON para feed masivo Bumeran Peru
        - LINKEDIN:     publicacion via API OAuth2 (simpleJobPostings)
        - PORTAL:       activacion en el portal de empleo propio (interno)
    """

    PLATAFORMA_CHOICES = [
        ('COMPUTRABAJO', 'Computrabajo Peru'),
        ('BUMERAN',      'Bumeran Peru'),
        ('LINKEDIN',     'LinkedIn Jobs'),
        ('PORTAL',       'Portal de Empleo Propio'),
    ]

    ESTADO_CHOICES = [
        ('OK',    'Exitoso'),
        ('ERROR', 'Error'),
    ]

    vacante = models.ForeignKey(
        'reclutamiento.Vacante',
        on_delete=models.CASCADE,
        related_name='logs_publicacion',
        verbose_name='Vacante',
    )
    plataforma = models.CharField(
        max_length=15,
        choices=PLATAFORMA_CHOICES,
        verbose_name='Plataforma',
    )
    estado = models.CharField(
        max_length=5,
        choices=ESTADO_CHOICES,
        default='OK',
        verbose_name='Estado',
    )
    url_publicada = models.URLField(
        blank=True,
        verbose_name='URL Publicada',
        help_text='URL de la oferta en la plataforma externa (si aplica)',
    )
    respuesta_api = models.TextField(
        blank=True,
        verbose_name='Respuesta API',
        help_text='JSON o mensaje de respuesta devuelto por la plataforma',
    )
    mensaje = models.TextField(
        blank=True,
        verbose_name='Mensaje',
        help_text='Mensaje de exito o descripcion del error',
    )
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='Publicado por',
    )
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name='Fecha/Hora')

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Log de Publicacion de Vacante'
        verbose_name_plural = 'Logs de Publicacion de Vacantes'
        indexes = [
            models.Index(fields=['vacante', 'plataforma']),
            models.Index(fields=['-creado_en']),
        ]

    def __str__(self):
        return (
            f'{self.get_plataforma_display()} — {self.vacante.titulo} '
            f'({self.get_estado_display()}) [{self.creado_en:%d/%m/%Y %H:%M}]'
        )
