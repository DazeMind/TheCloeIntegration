from rest_framework import serializers
from .models import ConfiguracionIntegracion


class ConfiguracionIntegracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionIntegracion
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
