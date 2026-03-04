"""
Registro en Django Admin del modulo de Reclutamiento y Seleccion.
"""
from django.contrib import admin
from .models import (
    Vacante, EtapaPipeline, Postulacion,
    NotaPostulacion, EntrevistaPrograma,
)


@admin.register(Vacante)
class VacanteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'area', 'estado', 'prioridad', 'tipo_contrato', 'fecha_publicacion', 'fecha_limite')
    list_filter = ('estado', 'prioridad', 'tipo_contrato', 'area')
    search_fields = ('titulo', 'descripcion')
    date_hierarchy = 'creado_en'
    raw_id_fields = ('responsable', 'creado_por')


@admin.register(EtapaPipeline)
class EtapaPipelineAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'orden', 'color', 'activa', 'eliminable')
    list_editable = ('orden', 'activa')
    ordering = ('orden',)


@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'vacante', 'etapa', 'fuente', 'estado', 'fecha_postulacion')
    list_filter = ('estado', 'fuente', 'etapa', 'vacante')
    search_fields = ('nombre_completo', 'email')
    raw_id_fields = ('vacante', 'personal_creado')
    date_hierarchy = 'fecha_postulacion'


@admin.register(NotaPostulacion)
class NotaPostulacionAdmin(admin.ModelAdmin):
    list_display = ('postulacion', 'autor', 'tipo', 'fecha')
    list_filter = ('tipo',)
    raw_id_fields = ('postulacion', 'autor')


@admin.register(EntrevistaPrograma)
class EntrevistaProgramaAdmin(admin.ModelAdmin):
    list_display = ('postulacion', 'tipo', 'fecha_hora', 'entrevistador', 'modalidad', 'resultado')
    list_filter = ('tipo', 'modalidad', 'resultado')
    raw_id_fields = ('postulacion', 'entrevistador')
    date_hierarchy = 'fecha_hora'
