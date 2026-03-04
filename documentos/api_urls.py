"""
API URLs - Documentos.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import TipoDocumentoViewSet, DocumentoTrabajadorViewSet, BoletaPagoViewSet

router = DefaultRouter()
router.register(r'tipos', TipoDocumentoViewSet, basename='tipo-documento')
router.register(r'documentos', DocumentoTrabajadorViewSet, basename='documento-trabajador')
router.register(r'boletas', BoletaPagoViewSet, basename='boleta-pago')

urlpatterns = [
    path('', include(router.urls)),
]
