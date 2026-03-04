from django.urls import path
from . import views

urlpatterns = [
    path('', views.empresas_panel, name='empresas_panel'),
    path('nueva/', views.empresa_crear, name='empresa_crear'),
    path('<int:pk>/editar/', views.empresa_editar, name='empresa_editar'),
    path('seleccionar/', views.seleccionar_empresa, name='empresa_seleccionar'),
]
