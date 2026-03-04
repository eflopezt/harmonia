from django.contrib import admin
from core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'accion', 'content_type', 'object_id', 'descripcion', 'usuario', 'ip_address')
    list_filter = ('accion', 'content_type', 'usuario')
    search_fields = ('descripcion',)
    readonly_fields = ('content_type', 'object_id', 'accion', 'descripcion', 'cambios', 'usuario', 'ip_address', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
