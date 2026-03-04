"""
Calendario Laboral Compartido.
Gestiona eventos personalizados y consolida datos de vacaciones, permisos,
feriados, cumpleanos y turnos en una vista de calendario unificada.
"""
from django.conf import settings
from django.db import models

from personal.models import Personal, Area


class EventoCalendario(models.Model):
    """
    Evento personalizado del calendario.
    Los eventos de vacaciones, permisos, feriados, cumpleanos y turnos
    se obtienen dinamicamente desde sus modelos de origen; este modelo
    almacena unicamente los eventos creados manualmente.
    """

    TIPO_CHOICES = [
        ('VACACION', 'Vacaciones'),
        ('PERMISO', 'Permiso'),
        ('FERIADO', 'Feriado'),
        ('CUMPLEANOS', 'Cumpleanos'),
        ('TURNO', 'Turno'),
        ('REUNION', 'Reunion'),
        ('OTRO', 'Otro'),
    ]

    COLOR_POR_TIPO = {
        'VACACION': '#3b82f6',
        'PERMISO': '#f59e0b',
        'FERIADO': '#ef4444',
        'CUMPLEANOS': '#22c55e',
        'TURNO': '#8b5cf6',
        'REUNION': '#0f766e',
        'OTRO': '#6b7280',
    }

    titulo = models.CharField(max_length=200, verbose_name="Titulo")
    descripcion = models.TextField(blank=True, verbose_name="Descripcion")
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha Fin")
    tipo = models.CharField(
        max_length=12, choices=TIPO_CHOICES, default='OTRO',
        verbose_name="Tipo de Evento"
    )
    todo_el_dia = models.BooleanField(default=True, verbose_name="Todo el dia")
    personal = models.ForeignKey(
        Personal, on_delete=models.CASCADE, null=True, blank=True,
        related_name='eventos_calendario', verbose_name="Personal"
    )
    area = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='eventos_calendario', verbose_name="Area"
    )
    color = models.CharField(
        max_length=7, blank=True, verbose_name="Color",
        help_text="Hex color (#RRGGBB). Si vacio, se usa el color por tipo."
    )
    recurrente = models.BooleanField(default=False, verbose_name="Recurrente")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='eventos_creados',
        verbose_name="Creado por"
    )
    privado = models.BooleanField(
        default=False, verbose_name="Privado",
        help_text="Si es privado, solo el creador y el personal asignado lo ven."
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evento de Calendario"
        verbose_name_plural = "Eventos de Calendario"
        ordering = ['fecha_inicio']
        indexes = [
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
            models.Index(fields=['tipo']),
            models.Index(fields=['personal']),
            models.Index(fields=['area']),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio} - {self.fecha_fin})"

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = self.COLOR_POR_TIPO.get(self.tipo, '#6b7280')
        if not self.fecha_fin:
            self.fecha_fin = self.fecha_inicio
        super().save(*args, **kwargs)

    def get_color(self):
        """Retorna el color del evento (explicito o por tipo)."""
        return self.color or self.COLOR_POR_TIPO.get(self.tipo, '#6b7280')
