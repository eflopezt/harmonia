"""
API Serializers — Vacaciones y Permisos.
"""
from rest_framework import serializers
from .models import SaldoVacacional, SolicitudVacacion, SolicitudPermiso


class SaldoVacacionalSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)

    class Meta:
        model = SaldoVacacional
        fields = [
            'id', 'personal', 'personal_nombre',
            'periodo_inicio', 'periodo_fin',
            'dias_derecho', 'dias_gozados', 'dias_vendidos',
            'dias_pendientes', 'dias_truncos', 'estado',
            'observaciones', 'creado_en',
        ]
        read_only_fields = fields


class SolicitudVacacionSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)

    class Meta:
        model = SolicitudVacacion
        fields = [
            'id', 'personal', 'personal_nombre', 'saldo',
            'fecha_inicio', 'fecha_fin',
            'dias_calendario', 'dias_habiles',
            'motivo', 'estado',
            'aprobado_por', 'fecha_aprobacion', 'motivo_rechazo',
            'creado_en',
        ]
        read_only_fields = [
            'id', 'personal_nombre', 'estado',
            'aprobado_por', 'fecha_aprobacion', 'creado_en',
        ]


class SolicitudPermisoSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)
    tipo_nombre = serializers.CharField(
        source='tipo.nombre', read_only=True, default='')

    class Meta:
        model = SolicitudPermiso
        fields = [
            'id', 'personal', 'personal_nombre',
            'tipo', 'tipo_nombre',
            'fecha_inicio', 'fecha_fin', 'dias', 'horas',
            'motivo', 'estado',
            'aprobado_por', 'fecha_aprobacion', 'motivo_rechazo',
            'creado_en',
        ]
        read_only_fields = [
            'id', 'personal_nombre', 'tipo_nombre', 'estado',
            'aprobado_por', 'fecha_aprobacion', 'creado_en',
        ]
