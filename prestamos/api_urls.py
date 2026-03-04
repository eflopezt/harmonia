"""
API URLs — Préstamos y Adelantos.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import TipoPrestamoViewSet, PrestamoViewSet, CuotaPrestamoViewSet

router = DefaultRouter()
router.register(r'tipos', TipoPrestamoViewSet, basename='tipo-prestamo')
router.register(r'prestamos', PrestamoViewSet, basename='prestamo')
router.register(r'cuotas', CuotaPrestamoViewSet, basename='cuota-prestamo')

urlpatterns = [
    path('', include(router.urls)),
]
