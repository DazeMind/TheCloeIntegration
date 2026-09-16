import uuid
from django.db import models
from django.db.models import Q


class Empresa(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    rut_emisor = models.CharField(max_length=12, unique=True, verbose_name='RUT emisor')
    razon_social = models.CharField(max_length=200)
    nombre_fantasia = models.CharField(max_length=200, null=True, blank=True)
    giro = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(max_length=150, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    comuna = models.CharField(max_length=100, null=True, blank=True)
    ciudad = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    codigo_postal = models.CharField(max_length=10, null=True, blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'empresas'
        ordering = ['razon_social']
        verbose_name = 'Empresa'

    def __str__(self):
        return f"{self.razon_social} ({self.rut_emisor})"


class CertificadoDigital(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='certificados')
    nombre = models.CharField(max_length=100)
    archivo_pfx_url = models.CharField(
        max_length=500, null=True, blank=True,
        help_text='Referencia al archivo; el binario NO va en BD'
    )
    password_cifrada = models.CharField(
        max_length=500, null=True, blank=True,
        help_text='Cifrado AES-256 en la aplicación, NUNCA en claro'
    )
    emisor = models.CharField(max_length=200, null=True, blank=True)
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_expiracion = models.DateField()
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'certificados_digitales'
        ordering = ['fecha_expiracion']

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"


class ConfiguracionEmpresa(models.Model):
    AMBIENTE_CHOICES = [
        ('produccion', 'Producción'),
        ('testing', 'Testing / Homologación'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='configuraciones')
    ambiente = models.CharField(max_length=20, choices=AMBIENTE_CHOICES, default='testing')
    timbrado = models.CharField(max_length=20, null=True, blank=True)
    prefijo_folio = models.CharField(max_length=10, default='F')
    certificado = models.ForeignKey(
        CertificadoDigital, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuraciones_empresa'
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'ambiente'],
                condition=Q(activa=True),
                name='uq_config_empresa_ambiente_activa'
            ),
        ]

    def __str__(self):
        return f"Config {self.empresa.razon_social} ({self.ambiente})"
