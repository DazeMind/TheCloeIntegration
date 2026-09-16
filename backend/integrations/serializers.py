from rest_framework import serializers
from .models import DocumentoTributario


class ItemVentaSerializer(serializers.Serializer):
    nombre_producto = serializers.CharField(max_length=200)
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=1)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate(self, attrs):
        if attrs['cantidad'] < 1:
            raise serializers.ValidationError("La cantidad debe ser al menos 1.")
        if attrs['precio_unitario'] <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor a 0.")
        return attrs


class VentaEmitirSerializer(serializers.Serializer):
    empresa_id = serializers.IntegerField(required=False, help_text='ID de empresa; si no se envía, usa la primera activa')
    id_venta_origen = serializers.CharField(max_length=100)
    items = ItemVentaSerializer(many=True, min_length=1)

    def calculate_monto_total(self):
        return sum(
            item['cantidad'] * item['precio_unitario']
            for item in self.validated_data['items']
        )


class DocumentoTributarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoTributario
        fields = [
            'id', 'id_venta_origen', 'folio', 'tipo_documento',
            'estado', 'monto_total', 'fecha_creacion', 'empresa',
        ]
        read_only_fields = ['fecha_creacion']


class ConsultaVentaSerializer(serializers.Serializer):
    id_venta_origen = serializers.CharField(max_length=100)

    def validate_id_venta_origen(self, value):
        if not value.strip():
            raise serializers.ValidationError("id_venta_origen no puede estar vacío.")
        return value
