from rest_framework import serializers
from .models import Empresa, ConfiguracionEmpresa


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'rut_emisor', 'razon_social', 'activa', 'fecha_creacion']
        read_only_fields = ['fecha_creacion']


class ConfiguracionEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionEmpresa
        fields = ['id', 'empresa', 'ambiente', 'timbrado', 'prefijo_folio', 'certificado', 'activa']
