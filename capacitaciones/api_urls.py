"""
API URLs — Capacitaciones.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    CapacitacionViewSet,
    RequerimientoCapacitacionViewSet,
    CertificacionTrabajadorViewSet,
)

router = DefaultRouter()
router.register(r'capacitaciones', CapacitacionViewSet, basename='capacitacion')
router.register(r'requerimientos', RequerimientoCapacitacionViewSet, basename='requerimiento')
router.register(r'certificaciones', CertificacionTrabajadorViewSet, basename='certificacion')

urlpatterns = [
    path('', include(router.urls)),
]
