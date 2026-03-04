"""Admin del modulo Calendario Laboral."""
from django.contrib import admin

from .models import EventoCalendario


@admin.register(EventoCalendario)
class EventoCalendarioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'fecha_inicio', 'fecha_fin', 'personal',
                    'area', 'todo_el_dia', 'privado', 'creado_por')
    list_filter = ('tipo', 'todo_el_dia', 'privado', 'recurrente')
    search_fields = ('titulo', 'descripcion', 'personal__apellidos_nombres')
    date_hierarchy = 'fecha_inicio'
    raw_id_fields = ('personal', 'creado_por')
    readonly_fields = ('creado_en', 'actualizado_en')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
