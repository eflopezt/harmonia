"""
Vistas del módulo Tareo.

Re-exporta todas las vistas para mantener compatibilidad con urls.py:
    from asistencia import views
    views.tareo_dashboard(...)
"""
from asistencia.views.dashboard import tareo_dashboard  # noqa: F401
from asistencia.views.staff import vista_staff, ajax_staff_data  # noqa: F401
from asistencia.views.rco import vista_rco, ajax_rco_data  # noqa: F401
from asistencia.views.banco import banco_horas_view  # noqa: F401
from asistencia.views.importaciones import (  # noqa: F401
    importar_view,
    importar_synkro_view,
    importar_sunat_view,
    importar_s10_view,
    ajax_importaciones,
)
from asistencia.views.exportaciones import (  # noqa: F401
    exportar_carga_s10_view,
    exportar_cierre_view,
)
from asistencia.views.configuracion import (  # noqa: F401
    configuracion_view,
    parametros_view,
    feriado_crear,
    feriado_editar,
    feriado_eliminar,
    feriados_cargar_peru,
    homologacion_crear,
    homologacion_editar,
    homologacion_eliminar,
    regimen_crear,
    regimen_editar,
    regimen_eliminar,
    horario_crear,
    horario_editar,
    horario_eliminar,
    ia_test_connection,
)
from asistencia.views.kpis import kpi_dashboard_view  # noqa: F401
from asistencia.views.vista_unificada import vista_unificada  # noqa: F401
from asistencia.views.papeletas import (  # noqa: F401
    papeletas_view,
    papeleta_crear,
    papeleta_editar,
    papeleta_eliminar,
    papeleta_aprobar,
    papeletas_exportar,
)
from asistencia.views.solicitudes_he import (  # noqa: F401
    solicitudes_he_view,
    solicitud_he_crear,
    solicitud_he_editar,
    solicitud_he_eliminar,
)
from asistencia.views.justificaciones import (  # noqa: F401
    justificaciones_view,
    justificacion_revisar,
    justificacion_eliminar,
)
from asistencia.views.relojes import (  # noqa: F401
    lista_relojes,
    crear_reloj,
    editar_reloj,
    eliminar_reloj,
    detalle_reloj,
    ajax_test_reloj,
    ajax_sync_reloj,
    ajax_procesar_reloj,
    ajax_usuarios_reloj,
)
from asistencia.views.biometrico import (  # noqa: F401
    panel_biometrico,
    agregar_dispositivo,
    test_dispositivo,
    logs_sincronizacion,
)
