"""
API URLs — Reclutamiento.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import VacanteViewSet, EtapaPipelineViewSet, PostulacionViewSet

router = DefaultRouter()
router.register(r'etapas', EtapaPipelineViewSet, basename='etapa-pipeline')
router.register(r'vacantes', VacanteViewSet, basename='vacante')
router.register(r'postulaciones', PostulacionViewSet, basename='postulacion')

urlpatterns = [
    path('', include(router.urls)),
]
