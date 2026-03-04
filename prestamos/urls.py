"""URLs del módulo de Préstamos."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.prestamos_panel, name='prestamos_panel'),
    path('nuevo/', views.prestamo_crear, name='prestamo_crear'),
    path('<int:pk>/', views.prestamo_detalle, name='prestamo_detalle'),
    path('<int:pk>/aprobar/', views.prestamo_aprobar, name='prestamo_aprobar'),
    path('<int:pk>/cancelar/', views.prestamo_cancelar, name='prestamo_cancelar'),
    path('cuota/<int:pk>/pagar/', views.cuota_pagar, name='cuota_pagar'),
    path('mis/', views.mis_prestamos, name='mis_prestamos'),
]
