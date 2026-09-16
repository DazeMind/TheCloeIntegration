import logging

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from configurations.models import Empresa
from integrations.models import (
    AgenteIntegracion,
    DetalleDocumento,
    DocumentoTributario,
    HistoricoEstadoDocumento,
    LogConsultaAPI,
)
from .services.dte_payload_builder import build_dte_payload, monto_linea_clp
from .services.simplefactura_client import SimpleFacturaClient
from .models import Venta

logger = logging.getLogger(__name__)

TIPO_DTE = {'BOLETA': 39, 'INVOICE': 33}

# Reintentos django-q2 (v1.11): NO existen retry/max_retries per-task.
# Son globales del cluster: redelivery cada Conf.RETRY (180s) hasta
# Conf.MAX_ATTEMPTS (3). Ver Q_CLUSTER en config/settings.py.


def _agente_simplefactura():
    agente, _ = AgenteIntegracion.objects.get_or_create(
        nombre='SIMPLEFACTURA',
        defaults={
            'tipo': 'SISTEMA',
            'descripcion': 'Emisión de DTE a través de la API de SimpleFactura',
        },
    )
    return agente


def _rut_receptor(venta):
    return (venta.cliente_rut or '').strip() or '66666666-6'


def _razon_social_receptor(venta):
    return (venta.cliente_nombre or '').strip() or 'Consumidor Final'


def _registrar_estado(doc, estado_nuevo, motivo, agente):
    """Cambia estado del DTE y deja trazabilidad. No registra si no cambia."""
    anterior = doc.estado
    if anterior == estado_nuevo:
        return
    doc.estado = estado_nuevo
    doc.save(update_fields=['estado', 'fecha_actualizacion'])
    HistoricoEstadoDocumento.objects.create(
        documento=doc,
        estado_anterior=anterior,
        estado_nuevo=estado_nuevo,
        motivo=(motivo or '')[:250],
        agente=agente,
    )


def _log_api(agente, endpoint, payload, respuesta, http_status, duracion_ms,
             mensaje_error=None):
    LogConsultaAPI.objects.create(
        agente=agente,
        endpoint=endpoint[:255],
        metodo_http='POST',
        codigo_respuesta_http=http_status,
        payload_enviado=payload,
        respuesta_recibida=respuesta,
        mensaje_error=mensaje_error,
        duracion_ms=duracion_ms,
    )


def _get_o_crear_documento(venta, empresa, tipo, respuesta, agente):
    """Obtiene o crea el DocumentoTributario de la venta (unique empresa+venta+tipo).

    Se crea en estado PENDIENTE; quién lo use transiciona el estado vía
    _registrar_estado() para dejar trazabilidad en HistoricoEstadoDocumento.
    """
    datos = {
        'folio': None,
        'rut_emisor': empresa.rut_emisor,
        'rut_receptor': _rut_receptor(venta),
        'razon_social_receptor': _razon_social_receptor(venta),
        'monto_total': venta.monto_total,
        'respuesta_sii_json': respuesta or None,
        'fecha_emision': venta.issued_at,
        'intentos': 0,
    }
    doc, created = DocumentoTributario.objects.get_or_create(
        empresa=empresa,
        id_venta_origen=venta.sale_id,
        tipo_documento=tipo,
        defaults={**datos, 'estado': 'PENDIENTE'},
    )
    if not created:
        for campo, valor in datos.items():
            setattr(doc, campo, valor)
        doc.save()
    return doc, created


def _sincronizar_detalles(doc, venta):
    """Refresca DetalleDocumento a partir de los detalles de la venta."""
    for detalle in venta.detalles.all().order_by('linea'):
        DetalleDocumento.objects.update_or_create(
            documento=doc,
            linea=detalle.linea,
            defaults={
                'nombre_producto': detalle.nombre_producto,
                'codigo_producto': detalle.codigo_producto,
                'cantidad': detalle.cantidad,
                'precio_unitario': detalle.precio_unitario,
                'monto_linea': monto_linea_clp(detalle),
            },
        )


def _marcar_emitida(venta, empresa, agente, payload, respuesta, http_status,
                    tipo, duracion_ms, endpoint):
    folio = int(respuesta['data']['folio'])
    doc, _created = _get_o_crear_documento(venta, empresa, tipo, respuesta, agente)
    doc.folio = folio
    doc.rut_emisor = empresa.rut_emisor
    doc.rut_receptor = _rut_receptor(venta)
    doc.razon_social_receptor = _razon_social_receptor(venta)
    doc.monto_total = venta.monto_total
    doc.respuesta_sii_json = respuesta
    doc.fecha_emision = venta.issued_at
    doc.save()

    _sincronizar_detalles(doc, venta)
    _registrar_estado(doc, 'ACEPTADO', f'Emisión SimpleFactura folio {folio}', agente)

    venta.documento = doc
    venta.status = 'EMITTED'
    venta.error_mensaje = None
    venta.save(update_fields=['documento', 'status', 'error_mensaje', 'fecha_actualizacion'])

    _log_api(agente, endpoint, payload, respuesta, http_status, duracion_ms)
    logger.info('Venta %s EMITIDA (tipo=%s folio=%s)', venta.sale_id, tipo, folio)


def _marcar_fallida(venta, empresa, agente, payload, respuesta, http_status,
                    tipo, duracion_ms, endpoint, mensaje):
    # El DTE queda en ERROR para trazabilidad; el reintento lo llevará a ACEPTADO.
    doc, _created = _get_o_crear_documento(venta, empresa, tipo, respuesta, agente)
    _registrar_estado(doc, 'ERROR', 'Falló la emisión en SimpleFactura', agente)

    venta.status = 'FAILED'
    venta.error_mensaje = mensaje
    venta.save(update_fields=['status', 'error_mensaje', 'fecha_actualizacion'])

    _log_api(agente, endpoint, payload, respuesta, http_status, duracion_ms, mensaje)
    logger.error('Venta %s FALLIDA: %s', venta.sale_id, mensaje)


def _mensaje_error(respuesta, http_status):
    if http_status is None:
        return 'Sin respuesta de SimpleFactura (error de red).'
    if not isinstance(respuesta, dict):
        return f'Respuesta inesperada HTTP {http_status}.'
    if respuesta.get('errors'):
        return f"HTTP {http_status}: {respuesta['errors']}"
    return f"Emisión rechazada por SimpleFactura (HTTP {http_status}): {respuesta.get('message', respuesta)}"


def procesar_venta(venta_id, **kwargs):
    """
    Worker django-q: emite el DTE (boleta/factura) de una venta en SimpleFactura.

    Idempotente: si la venta ya está EMITTED con documento, sale sin tocar nada.
    En error marca la venta FAILED, deja registro y RE-LANZA para que django-q
    reintente. Reintentos globales del cluster: redelivery de la tarea fallida
    cada Conf.RETRY (180s), hasta max_attempts=3. Al agotarse, django-q abandona
    la tarea y la venta queda en FAILED para reproceso manual
    (manage.py procesar_ventas_pendientes --include-failed).
    """
    venta = (
        Venta.objects
        .select_related('empresa', 'documento')
        .prefetch_related('detalles')
        .get(pk=venta_id)
    )
    sale_id = venta.sale_id
    documento = venta.documento

    # Idempotencia real: ya emitida.
    if venta.status == 'EMITTED' and documento is not None:
        logger.info('Venta %s ya emitida (folio %s). Nada que hacer.', sale_id, documento.folio)
        return

    empresa = venta.empresa or Empresa.objects.filter(activa=True).first()
    if empresa is None:
        mensaje = 'No hay empresa asignada ni empresa activa para emitir el DTE.'
        logger.error('Venta %s: %s', sale_id, mensaje)
        venta.status = 'FAILED'
        venta.error_mensaje = mensaje
        venta.save(update_fields=['status', 'error_mensaje', 'fecha_actualizacion'])
        raise RuntimeError(mensaje)

    agente = _agente_simplefactura()

    venta.status = 'PROCESSING'
    venta.error_mensaje = None
    venta.save(update_fields=['status', 'error_mensaje', 'fecha_actualizacion'])

    try:
        payload = build_dte_payload(venta, empresa)
    except Exception as exc:
        mensaje = f'Error construyendo payload DTE: {exc}'
        _marcar_fallida(venta, empresa, agente, None, None, None,
                        TIPO_DTE[venta.document_type], 0, None, mensaje)
        raise RuntimeError(mensaje)

    tipo = TIPO_DTE[venta.document_type]
    sucursal = settings.SIMPLEFACTURA_SUCURSAL
    endpoint = f'/invoiceV2/{sucursal}'

    cliente = SimpleFacturaClient()
    inicio = timezone.now()
    try:
        respuesta, http_status = cliente.emitir_dte(payload)
    except Exception as exc:  # defensivo: el cliente no debe lanzar, por si cambia
        mensaje = f'Excepción no controlada en emisión: {exc}'
        _marcar_fallida(venta, empresa, agente, payload, None, None, tipo, 0, endpoint, mensaje)
        raise RuntimeError(mensaje)
    duracion_ms = max(int((timezone.now() - inicio).total_seconds() * 1000), 0)

    es_ok = (
        http_status == 200
        and isinstance(respuesta, dict)
        and respuesta.get('data') is not None
        and respuesta['data'].get('folio') is not None
    )

    if not es_ok:
        mensaje = _mensaje_error(respuesta, http_status)
        _marcar_fallida(venta, empresa, agente, payload, respuesta, http_status,
                        tipo, duracion_ms, endpoint, mensaje)
        raise RuntimeError(mensaje)

    try:
        _marcar_emitida(venta, empresa, agente, payload, respuesta, http_status,
                        tipo, duracion_ms, endpoint)
    except IntegrityError as exc:
        # Carrera entre workers/reintento: otro proceso ya creó el DTE.
        logger.warning('IntegrityError al emitir %s (%s) - recuperando DTE existente.', sale_id, exc)
        doc = DocumentoTributario.objects.get(
            empresa=empresa, id_venta_origen=venta.sale_id, tipo_documento=tipo
        )
        venta.documento = doc
        venta.status = 'EMITTED'
        venta.save(update_fields=['documento', 'status', 'fecha_actualizacion'])