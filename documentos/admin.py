from django.contrib import admin
from documentos.models import (
    CategoriaDocumento, TipoDocumento, DocumentoTrabajador, PlantillaConstancia,
    PlantillaDossier, PlantillaDossierItem, Dossier, DossierPersonal, DossierItem,
)


@admin.register(CategoriaDocumento)
class CategoriaDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'icono', 'orden', 'activa')
    list_editable = ('orden', 'activa')


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'obligatorio', 'vence', 'dias_alerta_vencimiento', 'activo')
    list_filter = ('categoria', 'obligatorio', 'vence', 'activo')
    list_editable = ('obligatorio', 'vence', 'activo')


@admin.register(DocumentoTrabajador)
class DocumentoTrabajadorAdmin(admin.ModelAdmin):
    list_display = ('personal', 'tipo', 'estado', 'fecha_emision', 'fecha_vencimiento', 'version', 'subido_por')
    list_filter = ('estado', 'tipo__categoria', 'tipo')
    search_fields = ('personal__apellidos_nombres', 'personal__nro_doc')
    raw_id_fields = ('personal',)


@admin.register(PlantillaConstancia)
class PlantillaConstanciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'categoria', 'activa', 'orden')
    list_filter = ('categoria', 'activa')
    list_editable = ('activa', 'orden')
    prepopulated_fields = {'codigo': ('nombre',)}


# ── Dossier ──────────────────────────────────────────────────────

class PlantillaDossierItemInline(admin.TabularInline):
    model = PlantillaDossierItem
    extra = 0
    fields = ('orden', 'seccion', 'tipo_documento', 'obligatorio', 'instruccion')
    ordering = ('orden',)


@admin.register(PlantillaDossier)
class PlantillaDossierAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activa', 'total_items', 'creado_en')
    list_filter = ('tipo', 'activa')
    list_editable = ('activa',)
    prepopulated_fields = {'codigo': ('nombre',)}
    inlines = [PlantillaDossierItemInline]


class DossierPersonalInline(admin.TabularInline):
    model = DossierPersonal
    extra = 0
    raw_id_fields = ('personal',)


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proyecto', 'estado', 'total_personal', 'progreso', 'fecha_entrega_prevista')
    list_filter = ('estado', 'plantilla')
    search_fields = ('nombre', 'proyecto', 'cliente')
    raw_id_fields = ('responsable', 'creado_por')
    inlines = [DossierPersonalInline]


@admin.register(DossierItem)
class DossierItemAdmin(admin.ModelAdmin):
    list_display = ('dossier', 'personal', 'tipo_documento', 'estado', 'orden')
    list_filter = ('estado', 'dossier')
    raw_id_fields = ('personal', 'documento')
