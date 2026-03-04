"""
API URLs — Vacaciones y Permisos.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    SaldoVacacionalViewSet,
    SolicitudVacacionViewSet,
    SolicitudPermisoViewSet,
)

router = DefaultRouter()
router.register(r'saldos', SaldoVacacionalViewSet, basename='saldo-vacacional')
router.register(r'solicitudes', SolicitudVacacionViewSet, basename='solicitud-vacacion')
router.register(r'permisos', SolicitudPermisoViewSet, basename='solicitud-permiso')

urlpatterns = [
    path('', include(router.urls)),
]
