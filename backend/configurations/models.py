from django.db import models


class ConfiguracionIntegracion(models.Model):
    """Configuración general de la integración tributaria."""

    AMBIENTE_CHOICES = [
        ('produccion', 'Producción'),
        ('testing', 'Testing / Homologación'),
    ]

    empresa = models.CharField(max_length=200)
    timbrado = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de timbrado vigente'
    )
    prefijo_folio = models.CharField(
        max_length=10,
        default='F',
        help_text='Prefijo para los folios generados'
    )
    ambiente = models.CharField(
        max_length=20,
        choices=AMBIENTE_CHOICES,
        default='produccion'
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_integracion'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Configuración de {self.empresa} ({self.ambiente})"
