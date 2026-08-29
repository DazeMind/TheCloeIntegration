from rest_framework import serializers
from .models import DocumentoTributario, LogConsulta


class ItemVentaSerializer(serializers.Serializer):
    nombre_producto = serializers.CharField(max_length=200)
    cantidad = serializers.IntegerField(min_value=1)
    precio_unitario = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, attrs):
        if attrs['cantidad'] < 1:
            raise serializers.ValidationError("La cantidad debe ser al menos 1.")
        if attrs['precio_unitario'] <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor a 0.")
        return attrs


class VentaEmitirSerializer(serializers.Serializer):
    id_venta = serializers.CharField(max_length=50)
    items = ItemVentaSerializer(many=True, min_length=1)

    def validate(self, attrs):
        return attrs

    def calculate_monto_total(self):
        return sum(
            item['cantidad'] * float(item['precio_unitario'])
            for item in self.validated_data['items']
        )


class DocumentoTributarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoTributario
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class ConsultaVentaSerializer(serializers.Serializer):
    id_venta = serializers.CharField(max_length=50)

    def validate_id_venta(self, value):
        if not value.strip():
            raise serializers.ValidationError("id_venta no puede estar vacío.")
        return value


class LogConsultaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogConsulta
        fields = '__all__'
        read_only_fields = ['fecha_consulta']
