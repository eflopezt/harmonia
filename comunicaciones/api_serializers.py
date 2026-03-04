"""
API Serializers — Comunicaciones.
"""
from rest_framework import serializers
from .models import Notificacion, ComunicadoMasivo


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = [
            'id', 'destinatario', 'destinatario_email',
            'asunto', 'cuerpo', 'tipo', 'estado',
            'enviada_en', 'leida_en', 'error_detalle',
            'metadata', 'creado_en',
        ]
        read_only_fields = fields


class ComunicadoMasivoSerializer(serializers.ModelSerializer):
    creado_por_nombre = serializers.CharField(
        source='creado_por.get_full_name', read_only=True, default='')

    class Meta:
        model = ComunicadoMasivo
        fields = [
            'id', 'titulo', 'cuerpo', 'tipo', 'estado',
            'destinatarios_tipo', 'grupo',
            'requiere_confirmacion',
            'programado_para', 'enviado_en',
            'creado_por', 'creado_por_nombre',
            'creado_en',
        ]
        read_only_fields = fields
