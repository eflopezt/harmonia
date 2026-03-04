from django.contrib import admin
from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display  = ('razon_social', 'ruc', 'regimen_laboral', 'sector', 'activa', 'es_principal')
    list_filter   = ('activa', 'es_principal', 'regimen_laboral', 'sector')
    search_fields = ('ruc', 'razon_social', 'nombre_comercial')
    readonly_fields = ('creado_en', 'actualizado_en', 'creado_por')
    fieldsets = (
        ('Identificación', {
            'fields': ('ruc', 'razon_social', 'nombre_comercial', 'codigo_empleador'),
        }),
        ('Dirección', {
            'fields': ('direccion', 'ubigeo', 'distrito', 'provincia', 'departamento'),
            'classes': ('collapse',),
        }),
        ('Contacto', {
            'fields': ('telefono', 'email_rrhh', 'web'),
            'classes': ('collapse',),
        }),
        ('Clasificación', {
            'fields': ('regimen_laboral', 'sector', 'actividad_economica'),
        }),
        ('Estado', {
            'fields': ('activa', 'es_principal'),
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'creado_en', 'actualizado_en'),
            'classes': ('collapse',),
        }),
    )
