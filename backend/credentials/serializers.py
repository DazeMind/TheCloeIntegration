from rest_framework import serializers
from .models import CredencialSimpleAPI


class CredencialSimpleAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = CredencialSimpleAPI
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
        extra_kwargs = {'api_key': {'write_only': True}}
