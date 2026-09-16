from django.contrib import admin
from .models import (
    AgenteIntegracion, LogConsultaAPI,
    DocumentoTributario, DetalleDocumento,
    HistoricoEstadoDocumento, LogConsultaIA,
)


class DetalleDocumentoInline(admin.TabularInline):
    model = DetalleDocumento
    extra = 0
    readonly_fields = ['nombre_producto', 'cantidad', 'precio_unitario', 'monto_linea']


class HistoricoEstadoDocumentoInline(admin.TabularInline):
    model = HistoricoEstadoDocumento
    extra = 0
    readonly_fields = ['estado_anterior', 'estado_nuevo', 'motivo', 'agente', 'fecha_cambio']


@admin.register(AgenteIntegracion)
class AgenteIntegracionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'activo', 'fecha_creacion']
    list_filter = ['tipo', 'activo']
    search_fields = ['nombre']


@admin.register(LogConsultaAPI)
class LogConsultaAPIAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'metodo_http', 'codigo_respuesta_http', 'duracion_ms', 'fecha_consulta']
    list_filter = ['metodo_http']
    search_fields = ['endpoint']
    date_hierarchy = 'fecha_consulta'


@admin.register(DocumentoTributario)
class DocumentoTributarioAdmin(admin.ModelAdmin):
    list_display = ['id_venta_origen', 'empresa', 'folio', 'tipo_documento', 'estado', 'monto_total', 'fecha_creacion']
    list_filter = ['estado', 'tipo_documento', 'empresa']
    search_fields = ['id_venta_origen', 'rut_receptor', 'folio']
    date_hierarchy = 'fecha_creacion'
    raw_id_fields = ['empresa']
    inlines = [DetalleDocumentoInline, HistoricoEstadoDocumentoInline]


@admin.register(LogConsultaIA)
class LogConsultaIAAdmin(admin.ModelAdmin):
    list_display = ['proveedor_ia', 'modelo', 'duracion_ms', 'tokens_completado', 'fecha_consulta']
    list_filter = ['proveedor_ia']
    search_fields = ['modelo']
    date_hierarchy = 'fecha_consulta'
