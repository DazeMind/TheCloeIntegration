from django.contrib import admin
from .models import DocumentoTributario, LogConsulta


@admin.register(DocumentoTributario)
class DocumentoTributarioAdmin(admin.ModelAdmin):
    list_display = ['id_venta', 'folio', 'estado', 'monto_total', 'fecha_creacion']
    list_filter = ['estado', 'tipo_documento']
    search_fields = ['id_venta', 'folio']
    date_hierarchy = 'fecha_creacion'


@admin.register(LogConsulta)
class LogConsultaAdmin(admin.ModelAdmin):
    list_display = ['tipo_consulta', 'id_venta_ref', 'fecha_consulta']
    list_filter = ['tipo_consulta']
    search_fields = ['id_venta_ref']
    date_hierarchy = 'fecha_consulta'
