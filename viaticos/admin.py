from django.contrib import admin

from .models import ConceptoViatico, AsignacionViatico, GastoViatico


class GastoInline(admin.TabularInline):
    model = GastoViatico
    extra = 0
    fields = ('concepto', 'fecha_gasto', 'monto', 'tipo_comprobante', 'numero_comprobante', 'estado')


@admin.register(ConceptoViatico)
class ConceptoViaticoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'tope_diario', 'requiere_comprobante', 'afecto_renta', 'activo')
    list_filter = ('activo', 'requiere_comprobante', 'afecto_renta')
    search_fields = ('nombre', 'codigo')


@admin.register(AsignacionViatico)
class AsignacionViaticoAdmin(admin.ModelAdmin):
    list_display = ('personal', 'periodo', 'monto_asignado', 'monto_rendido', 'estado', 'ubicacion')
    list_filter = ('estado', 'periodo')
    search_fields = ('personal__apellidos_nombres', 'personal__nro_doc')
    date_hierarchy = 'periodo'
    inlines = [GastoInline]


@admin.register(GastoViatico)
class GastoViaticoAdmin(admin.ModelAdmin):
    list_display = ('asignacion', 'concepto', 'fecha_gasto', 'monto', 'tipo_comprobante', 'estado')
    list_filter = ('estado', 'concepto', 'tipo_comprobante')
    search_fields = ('asignacion__personal__apellidos_nombres', 'descripcion', 'numero_comprobante')
