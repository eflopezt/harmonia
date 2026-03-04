"""
API Serializers - Documentos (Legajo Digital, Boletas).
"""
from rest_framework import serializers
from .models import TipoDocumento, DocumentoTrabajador, BoletaPago


class TipoDocumentoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source='categoria.nombre', read_only=True, default='')

    class Meta:
        model = TipoDocumento
        fields = [
            'id', 'nombre', 'categoria', 'categoria_nombre',
            'obligatorio', 'vence', 'dias_alerta_vencimiento',
            'aplica_staff', 'aplica_rco', 'activo', 'orden',
        ]
        read_only_fields = fields


class DocumentoTrabajadorSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)
    tipo_nombre = serializers.CharField(
        source='tipo.nombre', read_only=True)

    class Meta:
        model = DocumentoTrabajador
        fields = [
            'id', 'personal', 'personal_nombre',
            'tipo', 'tipo_nombre', 'nombre_archivo',
            'fecha_emision', 'fecha_vencimiento',
            'estado', 'notas', 'version',
            'creado_en', 'actualizado_en',
        ]
        read_only_fields = fields
        # NO exponer campo archivo (FileField) por seguridad


class BoletaPagoSerializer(serializers.ModelSerializer):
    personal_nombre = serializers.CharField(
        source='personal.apellidos_nombres', read_only=True)

    class Meta:
        model = BoletaPago
        fields = [
            'id', 'personal', 'personal_nombre',
            'periodo', 'tipo', 'nombre_archivo',
            'remuneracion_bruta', 'descuentos', 'neto_pagar',
            'estado', 'fecha_publicacion',
            'confirmada', 'fecha_confirmacion',
            'creado_en',
        ]
        read_only_fields = fields
        # NO exponer campo archivo ni IP
