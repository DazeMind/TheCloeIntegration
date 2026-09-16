from uuid import uuid4
from django.db import models
from django.db.models import Q
from django.utils import timezone
from configurations.models import Empresa


class AgenteIntegracion(models.Model):
    TIPO_CHOICES = [
        ('SISTEMA', 'Sistema'),
        ('USUARIO', 'Usuario'),
    ]

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='SISTEMA')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agentes_integracion'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class LogConsultaAPI(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    agente = models.ForeignKey(
        AgenteIntegracion, null=True, on_delete=models.SET_NULL, related_name='logs_api'
    )
    idempotency_key = models.UUIDField(null=True, blank=True, unique=False)
    endpoint = models.CharField(max_length=255)
    metodo_http = models.CharField(max_length=10)
    codigo_respuesta_http = models.IntegerField(null=True, blank=True)
    payload_enviado = models.JSONField(null=True, blank=True)
    respuesta_recibida = models.JSONField(null=True, blank=True)
    mensaje_error = models.TextField(null=True, blank=True)
    duracion_ms = models.IntegerField(null=True, blank=True)
    ip_origen = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    fecha_consulta = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs_consultas_api'
        ordering = ['-fecha_consulta']
        constraints = [
            models.UniqueConstraint(
                fields=['idempotency_key'],
                condition=Q(idempotency_key__isnull=False),
                name='uq_log_api_idempotency'
            ),
        ]

    def __str__(self):
        return f"{self.metodo_http} {self.endpoint} - {self.codigo_respuesta_http}"


class DocumentoTributario(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADO', 'Enviado'),
        ('ACEPTADO', 'Aceptado'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado'),
        ('ERROR', 'Error'),
    ]

    TIPO_DOCUMENTO_CHOICES = [
        (33, 'Factura'),
        (34, 'Factura Exenta'),
        (35, 'Boleta Exenta'),
        (38, 'Boleta'),
        (39, 'Boleta'),
        (41, 'Boleta Honorarios'),
        (46, 'Factura Compra'),
        (52, 'Guía de Despacho'),
        (56, 'Nota Débito'),
        (61, 'Nota Crédito'),
    ]

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    uuid_operacion = models.UUIDField(default=uuid4, unique=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='documentos')
    id_venta_origen = models.CharField(
        max_length=100,
        help_text='ID de venta en el sistema privado (correlación)'
    )
    tipo_documento = models.IntegerField(choices=TIPO_DOCUMENTO_CHOICES, default=39)
    folio = models.IntegerField(null=True, blank=True)
    track_id = models.CharField(max_length=100, null=True, blank=True)
    rut_emisor = models.CharField(max_length=12)
    rut_receptor = models.CharField(max_length=12)
    razon_social_receptor = models.CharField(max_length=200, null=True, blank=True)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    pdf_url = models.CharField(max_length=500, null=True, blank=True)
    xml_url = models.CharField(max_length=500, null=True, blank=True)
    respuesta_sii_json = models.JSONField(null=True, blank=True)
    codigo_estado_sii = models.IntegerField(null=True, blank=True)
    glosa_estado_sii = models.CharField(max_length=255, null=True, blank=True)
    documento_referencia = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.DO_NOTHING, related_name='documentos_referenciados'
    )
    tipo_referencia = models.IntegerField(null=True, blank=True)
    fecha_referencia = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField(max_length=250, null=True, blank=True)
    intentos = models.IntegerField(default=0)
    proximo_reintento = models.DateTimeField(null=True, blank=True)
    fecha_emision = models.DateTimeField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documentos_tributarios'
        ordering = ['-fecha_creacion']
        verbose_name = 'Documento Tributario'
        verbose_name_plural = 'Documentos Tributarios'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'id_venta_origen', 'tipo_documento'],
                name='uq_empresa_venta_tipo'
            ),
            models.CheckConstraint(
                check=Q(estado__in=['PENDIENTE', 'ENVIADO', 'ACEPTADO', 'RECHAZADO', 'ANULADO', 'ERROR']),
                name='chk_doc_estado'
            ),
            models.CheckConstraint(
                check=Q(tipo_documento__in=[33, 34, 35, 38, 39, 41, 46, 52, 56, 61]),
                name='chk_doc_tipo'
            ),
        ]
        indexes = [
            models.Index(fields=['empresa', 'estado', '-fecha_creacion'], name='ix_doc_empresa_estado'),
            models.Index(fields=['track_id'], name='ix_doc_track_id'),
        ]

    def __str__(self):
        return f"{self.id_venta_origen} - Folio {self.folio} - {self.estado}"


class DetalleDocumento(models.Model):
    documento = models.ForeignKey(DocumentoTributario, on_delete=models.CASCADE, related_name='detalles')
    linea = models.IntegerField()
    nombre_producto = models.CharField(max_length=200)
    codigo_producto = models.CharField(max_length=50, null=True, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    monto_linea = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'detalles_documento'
        ordering = ['documento_id', 'linea']
        constraints = [
            models.UniqueConstraint(fields=['documento', 'linea'], name='uq_detalle_linea'),
        ]

    def __str__(self):
        return f"{self.nombre_producto} x{self.cantidad}"


class HistoricoEstadoDocumento(models.Model):
    documento = models.ForeignKey(
        DocumentoTributario, on_delete=models.CASCADE, related_name='historico_estados'
    )
    estado_anterior = models.CharField(max_length=20, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=20)
    motivo = models.CharField(max_length=250, null=True, blank=True)
    agente = models.ForeignKey(
        AgenteIntegracion, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historico_estados_documento'
        ordering = ['-fecha_cambio']
        constraints = [
            models.CheckConstraint(
                check=Q(estado_nuevo__in=['PENDIENTE', 'ENVIADO', 'ACEPTADO', 'RECHAZADO', 'ANULADO', 'ERROR']),
                name='chk_hist_estado'
            ),
        ]
        indexes = [
            models.Index(fields=['documento', '-fecha_cambio'], name='ix_hist_documento'),
        ]

    def __str__(self):
        return f"{self.documento} - {self.estado_anterior} → {self.estado_nuevo}"


class LogConsultaIA(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    agente = models.ForeignKey(
        AgenteIntegracion, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='logs_ia'
    )
    proveedor_ia = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    endpoint = models.CharField(max_length=255, null=True, blank=True)
    prompt_enviado = models.TextField(null=True, blank=True)
    respuesta_recibida = models.TextField(null=True, blank=True)
    mensaje_error = models.TextField(null=True, blank=True)
    tokens_prompt = models.IntegerField(null=True, blank=True)
    tokens_completado = models.IntegerField(null=True, blank=True)
    duracion_ms = models.IntegerField(null=True, blank=True)
    codigo_respuesta_http = models.IntegerField(null=True, blank=True)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    metadata_json = models.JSONField(null=True, blank=True)
    fecha_consulta = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs_consultas_ia'
        ordering = ['-fecha_consulta']

    def __str__(self):
        return f"{self.proveedor_ia} - {self.fecha_consulta}"
