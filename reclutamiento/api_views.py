"""
API Views — Reclutamiento y Selección.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Vacante, EtapaPipeline, Postulacion
from .api_serializers import (
    VacanteSerializer,
    VacanteListSerializer,
    EtapaPipelineSerializer,
    PostulacionSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Reclutamiento']),
    retrieve=extend_schema(tags=['Reclutamiento']),
)
class EtapaPipelineViewSet(viewsets.ReadOnlyModelViewSet):
    """Etapas del pipeline de selección."""
    queryset = EtapaPipeline.objects.filter(activa=True)
    serializer_class = EtapaPipelineSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['orden']


@extend_schema_view(
    list=extend_schema(tags=['Reclutamiento']),
    retrieve=extend_schema(tags=['Reclutamiento']),
)
class VacanteViewSet(viewsets.ReadOnlyModelViewSet):
    """Vacantes abiertas."""
    queryset = Vacante.objects.select_related('area', 'responsable').prefetch_related('postulaciones').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['area', 'estado', 'prioridad', 'tipo_contrato', 'publica']
    search_fields = ['titulo', 'descripcion', 'requisitos']
    ordering = ['-fecha_publicacion']

    def get_serializer_class(self):
        if self.action == 'list':
            return VacanteListSerializer
        return VacanteSerializer


@extend_schema_view(
    list=extend_schema(tags=['Reclutamiento']),
    retrieve=extend_schema(tags=['Reclutamiento']),
    create=extend_schema(tags=['Reclutamiento']),
)
class PostulacionViewSet(viewsets.ModelViewSet):
    """Postulaciones a vacantes (lectura + creación)."""
    queryset = Postulacion.objects.select_related('vacante', 'etapa').all()
    serializer_class = PostulacionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vacante', 'etapa', 'estado', 'fuente']
    search_fields = ['nombre_completo', 'email']
    ordering = ['-fecha_postulacion']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
