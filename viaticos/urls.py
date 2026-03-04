from django.urls import path

from . import views

urlpatterns = [
    # Admin — panel y CRUD
    path('', views.viaticos_panel, name='viaticos_panel'),
    path('dashboard/', views.viaticos_dashboard, name='viaticos_dashboard'),
    path('crear/', views.viatico_crear, name='viatico_crear'),
    path('<int:pk>/', views.viatico_detalle, name='viatico_detalle'),
    path('<int:pk>/entregar/', views.viatico_entregar, name='viatico_entregar'),
    path('<int:pk>/conciliar/', views.viatico_conciliar, name='viatico_conciliar'),
    path('<int:pk>/anular/', views.viatico_anular, name='viatico_anular'),
    path('exportar/', views.viaticos_exportar, name='viaticos_exportar'),
    path('exportar/excel/', views.exportar_viaticos_excel, name='viaticos_exportar_excel'),
    path('reporte/excel/', views.viaticos_reporte_excel, name='viaticos_reporte_excel'),
    path('conciliar-masivo/', views.conciliar_masivo, name='viaticos_conciliar_masivo'),

    # Gastos individuales (AJAX)
    path('<int:pk>/gasto/', views.gasto_agregar, name='gasto_agregar'),
    path('gasto/<int:gasto_id>/revisar/', views.gasto_revisar, name='gasto_revisar'),
    path('gasto/<int:gasto_id>/eliminar/', views.gasto_eliminar, name='gasto_eliminar'),

    # Portal
    path('mis/', views.mis_viaticos, name='mis_viaticos'),
]
