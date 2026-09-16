from rest_framework import serializers
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta


class ResumenReporteSerializer(serializers.Serializer):
    total_emisiones = serializers.IntegerField()
    emitidos = serializers.IntegerField()
    rechazados = serializers.IntegerField()
    pendientes = serializers.IntegerField()
    monto_total = serializers.FloatField()
    tasa_exito = serializers.FloatField()
    ultimos_7_dias = serializers.IntegerField()
    ultimos_30_dias = serializers.IntegerField()

    def to_representation(self, instance):
        return {
            "total_emisiones": self.context['total_emisiones'],
            "emitidos": self.context['emitidos'],
            "rechazados": self.context['rechazados'],
            "pendientes": self.context['pendientes'],
            "monto_total": self.context['monto_total'],
            "tasa_exito": self.context['tasa_exito'],
            "ultimos_7_dias": self.context['ultimos_7_dias'],
            "ultimos_30_dias": self.context['ultimos_30_dias'],
        }


class EstadoDocumentoSerializer(serializers.Serializer):
    estado = serializers.CharField()
    cantidad = serializers.IntegerField()
    monto_total = serializers.FloatField()