"""
API URLs — Salarios.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    BandaSalarialViewSet,
    HistorialSalarialViewSet,
    SimulacionIncrementoViewSet,
)

router = DefaultRouter()
router.register(r'bandas', BandaSalarialViewSet, basename='banda-salarial')
router.register(r'historial', HistorialSalarialViewSet, basename='historial-salarial')
router.register(r'simulaciones', SimulacionIncrementoViewSet, basename='simulacion')

urlpatterns = [
    path('', include(router.urls)),
]
