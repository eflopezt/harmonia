"""
API Serializers — Capacitaciones (LMS).
"""
from rest_framework import serializers
from .models import Capacitacion, RequerimientoCapacitacion, CertificacionTrabajador


class CapacitacionSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source='categoria.nombre', read_only=True, default='')

    class Meta:
        model = Capacitacion
        fields = [
            'id', 'titulo', 'descripcion',
            'categoria', 'categoria_nombre', 'tipo',
            'instructor', 'lugar',
            'fecha_inicio', 'fecha_fin', 'horas', 'costo',
            'max_participantes', 'estado', 'obligatoria',
            'material_url', 'creado_en',
        ]
        read_only_fields = fields


class RequerimientoCapacitacionSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source='categoria.nombre', read_only=True, default='')

    class Meta:
        model = RequerimientoCapacitacion
        fields = [
            'id', 'nombre', 'descripcion',
            'categoria', 'categoria_nombre',
            'aplica_todos', 'aplica_staff', 'aplica_rco',
            'frecuencia', 'horas_minimas', 'vigencia_dias',
            'base_legal', 'obligatorio', 'activo',
            'creado_en',
        ]
        read_only_fields = fields


class CertificacionTrabajadorSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)

    class Meta:
        model = CertificacionTrabajador
        fields = [
            'id', 'personal', 'personal_nombre',
            'requerimiento', 'capacitacion',
            'fecha_obtencion', 'fecha_vencimiento',
            'estado', 'creado_en',
        ]
        read_only_fields = fields
