from django.contrib import admin
from .models import Empresa, CertificadoDigital, ConfiguracionEmpresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['razon_social', 'rut_emisor', 'activa', 'fecha_creacion']
    list_filter = ['activa']
    search_fields = ['razon_social', 'rut_emisor']


@admin.register(CertificadoDigital)
class CertificadoDigitalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'empresa', 'fecha_emision', 'fecha_expiracion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']
    raw_id_fields = ['empresa']


@admin.register(ConfiguracionEmpresa)
class ConfiguracionEmpresaAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'ambiente', 'timbrado', 'prefijo_folio', 'activa', 'fecha_creacion']
    list_filter = ['ambiente', 'activa']
    search_fields = ['empresa__razon_social']
    raw_id_fields = ['empresa', 'certificado']
