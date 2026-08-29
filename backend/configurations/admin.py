from django.contrib import admin
from .models import ConfiguracionIntegracion


@admin.register(ConfiguracionIntegracion)
class ConfiguracionIntegracionAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'ambiente', 'timbrado', 'activa', 'fecha_creacion']
    list_filter = ['ambiente', 'activa']
    search_fields = ['empresa']
