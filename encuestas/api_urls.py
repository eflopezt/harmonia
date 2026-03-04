"""
API URLs — Encuestas.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import EncuestaViewSet, ResultadoEncuestaViewSet

router = DefaultRouter()
router.register(r'encuestas', EncuestaViewSet, basename='encuesta')
router.register(r'resultados', ResultadoEncuestaViewSet, basename='resultado-encuesta')

urlpatterns = [
    path('', include(router.urls)),
]
