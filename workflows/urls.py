from django.urls import path
from . import views

urlpatterns = [
    path('bandeja/', views.bandeja_aprobaciones, name='workflow_bandeja'),
    path('bandeja/resumen/', views.bandeja_resumen_ajax, name='workflow_bandeja_resumen'),
    path('bandeja/<int:pk>/', views.instancia_detalle, name='workflow_detalle'),
    path('bandeja/<int:pk>/decidir/', views.decidir_view, name='workflow_decidir'),
    path('bandeja/<int:pk>/cancelar/', views.cancelar_view, name='workflow_cancelar'),
    path('pasos/<int:pk>/escalar/', views.escalar_paso, name='workflow_escalar'),
    path('config/', views.flujos_config, name='workflow_config'),
    path('config/nuevo/', views.flujo_crear, name='workflow_crear'),
    path('config/<int:flujo_pk>/etapa/', views.etapa_crear, name='workflow_etapa_crear'),
    path('config/<int:pk>/toggle/', views.flujo_toggle_activo, name='flujo_toggle'),
    path('flujos/<int:pk>/diagrama/', views.flujo_diagrama_ajax, name='workflow_diagrama'),
]
