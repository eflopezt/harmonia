"""
API URLs — Analytics.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import KPISnapshotViewSet, AlertaRRHHViewSet

router = DefaultRouter()
router.register(r'snapshots', KPISnapshotViewSet, basename='kpi-snapshot')
router.register(r'alertas', AlertaRRHHViewSet, basename='alerta-rrhh')

urlpatterns = [
    path('', include(router.urls)),
]
