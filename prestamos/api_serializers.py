"""
API Serializers — Préstamos y Adelantos.
"""
from rest_framework import serializers
from .models import TipoPrestamo, Prestamo, CuotaPrestamo


class TipoPrestamoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPrestamo
        fields = [
            'id', 'nombre', 'codigo', 'descripcion',
            'max_cuotas', 'tasa_interes_mensual', 'monto_maximo',
            'requiere_aprobacion', 'activo',
        ]
        read_only_fields = fields


class CuotaPrestamoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuotaPrestamo
        fields = [
            'id', 'prestamo', 'numero', 'periodo',
            'monto', 'monto_pagado', 'estado', 'fecha_pago',
            'referencia_nomina',
        ]
        read_only_fields = fields


class PrestamoSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)
    tipo_nombre = serializers.CharField(
        source='tipo.nombre', read_only=True)
    cuotas = CuotaPrestamoSerializer(many=True, read_only=True)

    class Meta:
        model = Prestamo
        fields = [
            'id', 'personal', 'personal_nombre',
            'tipo', 'tipo_nombre',
            'monto_solicitado', 'monto_aprobado',
            'num_cuotas', 'cuota_mensual', 'tasa_interes',
            'fecha_solicitud', 'fecha_aprobacion', 'fecha_primer_descuento',
            'estado', 'motivo', 'observaciones',
            'creado_en', 'cuotas',
        ]
        read_only_fields = fields


class PrestamoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listado (sin cuotas anidadas)."""
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)
    tipo_nombre = serializers.CharField(
        source='tipo.nombre', read_only=True)

    class Meta:
        model = Prestamo
        fields = [
            'id', 'personal', 'personal_nombre',
            'tipo', 'tipo_nombre',
            'monto_solicitado', 'monto_aprobado',
            'num_cuotas', 'cuota_mensual',
            'estado', 'fecha_solicitud', 'creado_en',
        ]
        read_only_fields = fields
