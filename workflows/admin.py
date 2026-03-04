from django.contrib import admin
from .models import FlujoTrabajo, EtapaFlujo, InstanciaFlujo, PasoFlujo


class EtapaInline(admin.TabularInline):
    model  = EtapaFlujo
    extra  = 1
    fields = ['orden', 'nombre', 'tipo_aprobador', 'aprobador_usuario',
              'tiempo_limite_horas', 'accion_vencimiento']


@admin.register(FlujoTrabajo)
class FlujoTrabajoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'content_type', 'valor_trigger', 'total_etapas', 'activo']
    list_filter  = ['activo', 'content_type']
    inlines      = [EtapaInline]


@admin.register(InstanciaFlujo)
class InstanciaFlujoAdmin(admin.ModelAdmin):
    list_display    = ['pk', 'flujo', 'estado', 'solicitante', 'etapa_actual', 'iniciado_en']
    list_filter     = ['estado', 'flujo']
    readonly_fields = ['iniciado_en', 'completado_en', 'content_type', 'object_id']


@admin.register(PasoFlujo)
class PasoFlujoAdmin(admin.ModelAdmin):
    list_display = ['instancia', 'etapa', 'aprobador', 'decision', 'fecha']
    list_filter  = ['decision']
    readonly_fields = ['fecha']
