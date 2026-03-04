"""
Admin del módulo Comunicaciones Inteligentes.
"""
from django.contrib import admin
from comunicaciones.models import (
    ComunicadoMasivo, ConfiguracionSMTP, ConfirmacionLectura,
    Notificacion, PlantillaNotificacion, PreferenciaNotificacion,
)


@admin.register(PlantillaNotificacion)
class PlantillaNotificacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'modulo', 'tipo', 'activa', 'actualizado_en']
    list_filter = ['modulo', 'tipo', 'activa']
    search_fields = ['nombre', 'codigo']
    prepopulated_fields = {'codigo': ('nombre',)}


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['asunto', 'destinatario', 'tipo', 'estado', 'creado_en']
    list_filter = ['tipo', 'estado', 'creado_en']
    search_fields = ['asunto', 'destinatario__apellidos_nombres', 'destinatario_email']
    raw_id_fields = ['destinatario', 'plantilla']
    readonly_fields = ['creado_en']


@admin.register(ComunicadoMasivo)
class ComunicadoMasivoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'estado', 'destinatarios_tipo', 'creado_por', 'creado_en']
    list_filter = ['tipo', 'estado', 'destinatarios_tipo']
    search_fields = ['titulo']
    raw_id_fields = ['creado_por']
    filter_horizontal = ['areas', 'personal_individual']


@admin.register(ConfirmacionLectura)
class ConfirmacionLecturaAdmin(admin.ModelAdmin):
    list_display = ['comunicado', 'personal', 'fecha_lectura', 'confirmado']
    list_filter = ['confirmado', 'fecha_lectura']
    raw_id_fields = ['comunicado', 'personal']


@admin.register(PreferenciaNotificacion)
class PreferenciaNotificacionAdmin(admin.ModelAdmin):
    list_display = ['personal', 'recibir_email', 'recibir_in_app', 'frecuencia_resumen']
    list_filter = ['recibir_email', 'recibir_in_app', 'frecuencia_resumen']
    raw_id_fields = ['personal']


@admin.register(ConfiguracionSMTP)
class ConfiguracionSMTPAdmin(admin.ModelAdmin):
    list_display = ['smtp_host', 'smtp_port', 'smtp_user', 'activa']

    def has_add_permission(self, request):
        # Singleton: solo permitir si no existe
        return not ConfiguracionSMTP.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
