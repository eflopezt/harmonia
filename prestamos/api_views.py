"""
API Views — Préstamos y Adelantos.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import TipoPrestamo, Prestamo, CuotaPrestamo
from .api_serializers import (
    TipoPrestamoSerializer,
    PrestamoSerializer,
    PrestamoListSerializer,
    CuotaPrestamoSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['Préstamos']),
    retrieve=extend_schema(tags=['Préstamos']),
)
class TipoPrestamoViewSet(viewsets.ReadOnlyModelViewSet):
    """Tipos de préstamo configurados."""
    queryset = TipoPrestamo.objects.filter(activo=True)
    serializer_class = TipoPrestamoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']


@extend_schema_view(
    list=extend_schema(tags=['Préstamos']),
    retrieve=extend_schema(tags=['Préstamos']),
)
class PrestamoViewSet(viewsets.ReadOnlyModelViewSet):
    """Préstamos y adelantos."""
    queryset = Prestamo.objects.select_related('personal', 'tipo').prefetch_related('cuotas').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['personal', 'tipo', 'estado']
    search_fields = ['personal__apellidos_nombres']
    ordering = ['-fecha_solicitud']

    def get_serializer_class(self):
        if self.action == 'list':
            return PrestamoListSerializer
        return PrestamoSerializer


@extend_schema_view(
    list=extend_schema(tags=['Préstamos']),
    retrieve=extend_schema(tags=['Préstamos']),
)
class CuotaPrestamoViewSet(viewsets.ReadOnlyModelViewSet):
    """Cuotas de préstamos."""
    queryset = CuotaPrestamo.objects.select_related('prestamo', 'prestamo__personal').all()
    serializer_class = CuotaPrestamoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['prestamo', 'estado']
    ordering = ['numero']
