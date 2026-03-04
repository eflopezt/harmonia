"""
API Serializers — Analytics.
"""
from rest_framework import serializers
from .models import KPISnapshot, AlertaRRHH


class KPISnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPISnapshot
        fields = '__all__'
        read_only_fields = ['id', 'creado_en']


class AlertaRRHHSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(
        source='area.nombre', read_only=True, default='')

    class Meta:
        model = AlertaRRHH
        fields = [
            'id', 'titulo', 'descripcion', 'categoria', 'severidad',
            'estado', 'area', 'area_nombre',
            'valor_actual', 'valor_umbral',
            'creado_en',
        ]
        read_only_fields = fields
