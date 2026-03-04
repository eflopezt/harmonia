"""URLs del módulo Disciplinario."""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard ejecutivo
    path('dashboard/', views.disciplinaria_dashboard, name='disciplinaria_dashboard'),

    # Admin — Panel
    path('', views.disciplinaria_panel, name='disciplinaria_panel'),
    path('nueva/', views.medida_crear, name='medida_crear'),
    path('<int:pk>/', views.medida_detalle, name='medida_detalle'),
    path('<int:pk>/notificar/', views.medida_notificar, name='medida_notificar'),
    path('<int:pk>/resolver/', views.medida_resolver, name='medida_resolver'),

    # Timeline legal
    path('<int:pk>/timeline/', views.proceso_timeline, name='disciplinaria_timeline'),

    # Descargos
    path('<int:medida_pk>/descargo/', views.descargo_registrar, name='descargo_registrar'),
    path('descargo/<int:pk>/evaluar/', views.descargo_evaluar, name='descargo_evaluar'),

    # Config
    path('tipos-falta/', views.tipos_falta, name='tipos_falta'),
    path('tipos-falta/crear/', views.tipo_falta_crear, name='tipo_falta_crear'),

    # Historial
    path('historial/<int:personal_id>/', views.historial_trabajador, name='historial_disciplinario'),

    # Exportación Excel
    path('exportar/', views.exportar_reporte_disciplinario, name='disciplinaria_exportar'),

    # Reporte AJAX — por área (Chart.js)
    path('reporte-area/', views.disciplinaria_reporte_area, name='disciplinaria_reporte_area'),
]
