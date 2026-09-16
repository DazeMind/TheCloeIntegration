from uuid import uuid4

from django.db import models

from configurations.models import Empresa
from integrations.models import DocumentoTributario


class Venta(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('BOLETA', 'Boleta'),
        ('INVOICE', 'Factura'),
    ]

    METODO_PAGO_CHOICES = [
        ('CASH', 'Efectivo'),
        ('CARD', 'Tarjeta'),
        ('TRANSFER', 'Transferencia'),
        ('OTHER', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('RECEIVED', 'Recibida'),
        ('QUEUED', 'En cola'),
        ('PROCESSING', 'Procesando'),
        ('EMITTED', 'Emitida'),
        ('FAILED', 'Fallida'),
    ]

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    sale_id = models.CharField(max_length=100, unique=True)
    document_type = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    issued_at = models.DateTimeField()
    payment_method = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='CASH')
    status = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='RECEIVED')
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='ventas')
    documento = models.ForeignKey(
        DocumentoTributario, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='venta',
    )
    cliente_rut = models.CharField(max_length=12, null=True, blank=True)
    cliente_nombre = models.CharField(max_length=200, null=True, blank=True)
    cliente_direccion = models.CharField(max_length=250, null=True, blank=True)
    cliente_comuna = models.CharField(max_length=100, null=True, blank=True)
    cliente_ciudad = models.CharField(max_length=100, null=True, blank=True)
    error_mensaje = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ventas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.sale_id} - {self.status}"

    def calcular_monto_total(self):
        return sum(
            (detalle.cantidad * detalle.precio_unitario) - detalle.descuento
            for detalle in self.detalles.all()
        )


class DetalleVenta(models.Model):
    IMPUESTO_CHOICES = [
        ('IVA', 'IVA'),
        ('EXEMPT', 'Exento'),
    ]

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    linea = models.IntegerField()
    codigo_producto = models.CharField(max_length=50, null=True, blank=True)
    nombre_producto = models.CharField(max_length=200)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.CharField(max_length=10, choices=IMPUESTO_CHOICES, default='IVA')

    class Meta:
        db_table = 'detalles_venta'
        ordering = ['venta_id', 'linea']
        constraints = [
            models.UniqueConstraint(fields=['venta', 'linea'], name='uq_detalle_venta_linea'),
        ]

    def __str__(self):
        return f"{self.nombre_producto} x{self.cantidad}"