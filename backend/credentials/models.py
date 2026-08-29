from django.db import models


class CredencialSimpleAPI(models.Model):
    """Credenciales para conectarse a SimpleAPI (SII)."""

    nombre = models.CharField(
        max_length=100,
        help_text='Nombre descriptivo de estas credenciales'
    )
    api_key = models.CharField(
        max_length=255,
        help_text='API Key para SimpleAPI'
    )
    base_url = models.URLField(
        default='https://api.simpleapi.cl/api/v1',
        help_text='URL base de la API de SimpleAPI'
    )
    activa = models.BooleanField(
        default=True,
        help_text='Indica si estas credenciales están activas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credenciales_simpleapi'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} {'(activa)' if self.activa else '(inactiva)'}"
