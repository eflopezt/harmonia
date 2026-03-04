"""
API URLs — Comunicaciones.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import NotificacionViewSet, ComunicadoMasivoViewSet

router = DefaultRouter()
router.register(r'notificaciones', NotificacionViewSet, basename='notificacion')
router.register(r'comunicados', ComunicadoMasivoViewSet, basename='comunicado')

urlpatterns = [
    path('', include(router.urls)),
]
