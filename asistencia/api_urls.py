"""
API URLs — Asistencia (tareo).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import RegistroTareoViewSet, BancoHorasViewSet, configuracion_sistema_api

router = DefaultRouter()
router.register(r'tareos', RegistroTareoViewSet, basename='tareo')
router.register(r'banco-horas', BancoHorasViewSet, basename='banco-horas')

urlpatterns = [
    path('config/', configuracion_sistema_api, name='api_config_sistema'),
    path('', include(router.urls)),
]
