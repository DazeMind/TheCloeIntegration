from rest_framework import serializers

from .models import DetalleVenta, Venta


class SaleItemSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(max_length=200)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default=0)
    tax = serializers.ChoiceField(choices=DetalleVenta.IMPUESTO_CHOICES, default='IVA')


class SaleCustomerSerializer(serializers.Serializer):
    rut = serializers.CharField(max_length=12, required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(max_length=250, required=False, allow_null=True, allow_blank=True)
    commune = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)


class SaleCreateSerializer(serializers.Serializer):
    sale_id = serializers.CharField(max_length=100)
    document_type = serializers.ChoiceField(choices=Venta.TIPO_DOCUMENTO_CHOICES)
    issued_at = serializers.DateTimeField()
    customer = SaleCustomerSerializer(required=False, allow_null=True)
    items = SaleItemSerializer(many=True, min_length=1)
    payment_method = serializers.ChoiceField(choices=Venta.METODO_PAGO_CHOICES, default='CASH')

    def validate_sale_id(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError("sale_id is required and cannot be empty.")
        return value

    def validate(self, attrs):
        if attrs.get('document_type') == 'INVOICE':
            customer = attrs.get('customer') or {}
            missing_fields = [
                field for field in ('rut', 'name', 'address', 'commune', 'city')
                if not str(customer.get(field) or '').strip()
            ]
            if missing_fields:
                raise serializers.ValidationError(
                    "customer.rut, customer.name, customer.address, customer.commune and "
                    "customer.city are required for INVOICE. Missing: "
                    + ", ".join(f"customer.{field}" for field in missing_fields) + "."
                )
        return attrs


class SaleSerializer(serializers.ModelSerializer):
    sale_id = serializers.IntegerField(source='id', read_only=True)
    reference = serializers.CharField(source='sale_id', read_only=True)
    customer = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    document = serializers.SerializerMethodField()
    error = serializers.CharField(source='error_mensaje', read_only=True, allow_null=True)

    class Meta:
        model = Venta
        fields = [
            'sale_id', 'reference', 'document_type', 'status', 'payment_method',
            'issued_at', 'customer', 'items', 'monto_total', 'document', 'error',
        ]

    def get_customer(self, obj):
        return {
            "rut": obj.cliente_rut,
            "name": obj.cliente_nombre,
            "address": obj.cliente_direccion,
            "commune": obj.cliente_comuna,
            "city": obj.cliente_ciudad,
        }

    def get_items(self, obj):
        return [
            {
                "code": detalle.codigo_producto,
                "description": detalle.nombre_producto,
                "quantity": str(detalle.cantidad),
                "unit_price": str(detalle.precio_unitario),
                "discount": str(detalle.descuento),
                "tax": detalle.impuesto,
            }
            for detalle in obj.detalles.all()
        ]

    def get_document(self, obj):
        documento = obj.documento
        if documento is None:
            return None
        return {
            "folio": documento.folio,
            "track_id": documento.track_id,
            "pdf_url": documento.pdf_url,
            "xml_url": documento.xml_url,
            "monto_total": str(documento.monto_total),
        }