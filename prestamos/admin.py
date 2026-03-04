from django.contrib import admin
from .models import TipoPrestamo, Prestamo, CuotaPrestamo


@admin.register(TipoPrestamo)
class TipoPrestamoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'max_cuotas', 'tasa_interes_mensual', 'monto_maximo', 'activo']
    list_filter = ['activo']


class CuotaInline(admin.TabularInline):
    model = CuotaPrestamo
    extra = 0
    readonly_fields = ['numero', 'periodo', 'monto', 'monto_pagado', 'estado', 'fecha_pago']
    can_delete = False


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ['personal', 'tipo', 'monto_solicitado', 'num_cuotas', 'estado', 'fecha_solicitud']
    list_filter = ['estado', 'tipo']
    search_fields = ['personal__apellidos_nombres', 'personal__nro_doc']
    raw_id_fields = ['personal']
    inlines = [CuotaInline]
