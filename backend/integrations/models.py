from django.db import models


class DocumentoTributario(models.Model):
    """Modelo que registra cada documento tributario emitido vía SimpleAPI (SII)."""

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EMITIDO', 'Emitido'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado'),
    ]

    id_venta = models.CharField(
        max_length=50,
        unique=True,
        help_text='ID interno de la venta en The Cloe'
    )
    folio = models.IntegerField(
        null=True,
        blank=True,
        help_text='Folio asignado por el SII vía SimpleAPI'
    )
    tipo_documento = models.IntegerField(
        default=39,
        help_text='Tipo de documento SII (39 = Boleta)'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )
    respuesta_sii = models.JSONField(
        null=True,
        blank=True,
        help_text='Respuesta cruda del SII / SimpleAPI'
    )
    mensaje_error = models.TextField(
        null=True,
        blank=True,
        help_text='Mensaje de error si el estado es RECHAZADO'
    )
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monto total de la venta'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documentos_tributarios'
        ordering = ['-fecha_creacion']
        verbose_name = 'Documento Tributario'
        verbose_name_plural = 'Documentos Tributarios'

    def __str__(self):
        return f"{self.id_venta} - Folio {self.folio} - {self.estado}"


class LogConsulta(models.Model):
    """Log de consultas realizadas al sistema para trazabilidad."""

    TIPO_CONSULTA = [
        ('EMISION', 'Emisión de boleta'),
        ('CONSULTA', 'Consulta de estado'),
        ('REPORTE', 'Generación de reporte'),
    ]

    tipo_consulta = models.CharField(max_length=20, choices=TIPO_CONSULTA)
    id_venta_ref = models.CharField(max_length=50, null=True, blank=True)
    parametros = models.JSONField(null=True, blank=True)
    respuesta = models.JSONField(null=True, blank=True)
    fecha_consulta = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'log_consultas'
        ordering = ['-fecha_consulta']

    def __str__(self):
        return f"{self.tipo_consulta} - {self.id_venta_ref} - {self.fecha_consulta}"
