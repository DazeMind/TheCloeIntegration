import httpx
import time
from django.conf import settings
from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from configurations.models import Empresa
from .models import (
    AgenteIntegracion,
    DetalleDocumento,
    DocumentoTributario,
    HistoricoEstadoDocumento,
    LogConsultaAPI,
)
from .serializers import (
    VentaEmitirSerializer,
    DocumentoTributarioSerializer,
)
from core.circuit_breaker import CircuitBreaker

# Instancia global del Circuit Breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
)


class SimpleAPIException(Exception):
    def __init__(self, message, http_status=None):
        self.http_status = http_status
        super().__init__(message)


class IntegracionViewSet(viewsets.ViewSet):
    """
    ViewSet principal para la integración con SimpleAPI (SII).
    Emite boletas, consulta estado y genera reportes.
    """

    @staticmethod
    def _get_agente_system():
        agente, _ = AgenteIntegracion.objects.get_or_create(
            nombre='SYSTEM',
            defaults={
                'tipo': 'SISTEMA',
                'descripcion': 'Agente automático del sistema integrador',
            },
        )
        return agente

    def _call_simpleapi(self, payload):
        """Llama a SimpleAPI protegido por Circuit Breaker."""
        if not circuit_breaker.can_execute():
            raise SimpleAPIException(
                "Circuit Breaker OPEN: SimpleAPI no está respondiendo. "
                "Inténtelo más tarde."
            )

        headers = {
            "Authorization": f"Bearer {settings.SIMPLEAPI_KEY}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        try:
            with httpx.Client(timeout=settings.SIMPLEAPI_TIMEOUT) as client:
                response = client.post(
                    f"{settings.SIMPLEAPI_BASE_URL}/dte/emitir",
                    json=payload,
                    headers=headers,
                )
                duration_ms = int((time.monotonic() - start) * 1000)
                data = response.json() if response.content else {}
                if response.status_code >= 400:
                    circuit_breaker.record_failure()
                    raise SimpleAPIException(
                        f"SimpleAPI respondió {response.status_code}: {data}",
                        http_status=response.status_code,
                    )
                circuit_breaker.record_success()
                return data, response.status_code, duration_ms
        except httpx.HTTPError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            circuit_breaker.record_failure()
            raise SimpleAPIException(
                f"Error de conexión con SimpleAPI: {str(exc)}",
            )

    def _build_sii_payload(self, id_venta_origen, items, monto_total):
        """Construye el payload en formato SII para SimpleAPI."""
        return {
            "documento": {
                "Encabezado": {
                    "IdDoc": {"TipoDTE": 39},
                    "Totales": {"MontoTotal": str(monto_total)}
                },
                "Detalle": [
                    {
                        "NroLinDet": index + 1,
                        "NmbItem": item["nombre_producto"],
                        "QtyItem": str(item["cantidad"]),
                        "PrcItem": float(item["precio_unitario"]),
                        "MontoItem": float(item["cantidad"] * item["precio_unitario"])
                    }
                    for index, item in enumerate(items)
                ]
            }
        }

    @staticmethod
    def _client_ip(request):
        return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() \
            or request.META.get("REMOTE_ADDR")

    @action(detail=False, methods=['post'], url_path='emitir-boleta')
    def emitir_boleta(self, request):
        """Emite una boleta electrónica vía SimpleAPI."""
        serializer = VentaEmitirSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        id_venta_origen = data['id_venta_origen']
        items = data['items']

        if data.get('empresa_id'):
            try:
                empresa = Empresa.objects.get(pk=data['empresa_id'])
            except Empresa.DoesNotExist:
                return Response(
                    {"detail": "La empresa indicada no existe."},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            empresa = Empresa.objects.filter(activa=True).first()
            if not empresa:
                return Response(
                    {"detail": "No hay empresas activas configuradas."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Verificar que no exista ya una emisión para esta venta
        if DocumentoTributario.objects.filter(
            empresa=empresa, id_venta_origen=id_venta_origen, tipo_documento=39
        ).exists():
            return Response(
                {"detail": f"La venta {id_venta_origen} ya tiene una boleta emitida."},
                status=status.HTTP_409_CONFLICT
            )

        monto_total = sum(
            item['cantidad'] * item['precio_unitario']
            for item in items
        )

        agente = self._get_agente_system()

        doc = DocumentoTributario.objects.create(
            empresa=empresa,
            id_venta_origen=id_venta_origen,
            tipo_documento=39,
            rut_emisor=empresa.rut_emisor,
            rut_receptor='66666666-6',
            monto_total=monto_total,
            estado='PENDIENTE',
        )

        for idx, item in enumerate(items, start=1):
            DetalleDocumento.objects.create(
                documento=doc,
                linea=idx,
                nombre_producto=item['nombre_producto'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                monto_linea=item['cantidad'] * item['precio_unitario'],
            )

        HistoricoEstadoDocumento.objects.create(
            documento=doc,
            estado_anterior=None,
            estado_nuevo='PENDIENTE',
            motivo='Documento creado, pendiente de envío a SimpleAPI',
            agente=agente,
        )

        payload = self._build_sii_payload(id_venta_origen, items, monto_total)

        resultado_sii = None
        codigo_http = 0
        duracion_ms = 0
        error_msg = None
        try:
            resultado_sii, codigo_http, duracion_ms = self._call_simpleapi(payload)
        except SimpleAPIException as exc:
            error_msg = str(exc)
            codigo_http = exc.http_status or 0
            resultado_sii = {"error": error_msg}

        folio = resultado_sii.get("folio") if error_msg is None else None
        track_id = resultado_sii.get("track_id") if error_msg is None else None

        if error_msg is None:
            respuesta_estado = resultado_sii.get("estado")
            estados_validos = dict(DocumentoTributario.ESTADO_CHOICES)
            if respuesta_estado in estados_validos:
                nuevo_estado = respuesta_estado
            elif folio or track_id:
                nuevo_estado = 'ACEPTADO'
            else:
                nuevo_estado = 'ENVIADO'
            motivo = 'Respuesta recibida de SimpleAPI'
        else:
            nuevo_estado = 'ERROR'
            motivo = error_msg[:250]

        doc.folio = folio
        doc.track_id = track_id
        doc.estado = nuevo_estado
        doc.respuesta_sii_json = resultado_sii
        doc.codigo_estado_sii = (
            resultado_sii.get('codigo_estado_sii') or resultado_sii.get('codigo_estado')
        ) if error_msg is None else None
        doc.glosa_estado_sii = (
            resultado_sii.get('glosa_estado_sii') or resultado_sii.get('glosa_estado')
        ) if error_msg is None else None
        doc.save(update_fields=[
            'folio', 'track_id', 'estado', 'respuesta_sii_json',
            'codigo_estado_sii', 'glosa_estado_sii', 'fecha_actualizacion',
        ])

        HistoricoEstadoDocumento.objects.create(
            documento=doc,
            estado_anterior='PENDIENTE',
            estado_nuevo=nuevo_estado,
            motivo=motivo,
            agente=agente,
        )

        LogConsultaAPI.objects.create(
            agente=agente,
            idempotency_key=doc.uuid_operacion,
            endpoint='/dte/emitir',
            metodo_http='POST',
            codigo_respuesta_http=codigo_http,
            payload_enviado=payload,
            respuesta_recibida=resultado_sii if error_msg is None else None,
            mensaje_error=error_msg,
            duracion_ms=duracion_ms,
            ip_origen=self._client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )

        return Response({
            "id": doc.id,
            "id_venta_origen": id_venta_origen,
            "folio": folio,
            "estado": nuevo_estado,
            "monto_total": float(monto_total),
            "tipo_documento": 39,
            "message": "Boleta emitida correctamente" if error_msg is None else
                       "Boleta registrada con errores de emisión",
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='consulta/(?P<id_venta_origen>[^/.]+)')
    def consultar_venta(self, request, id_venta_origen=None):
        """Consulta el estado de una venta por su ID de origen."""
        docs = DocumentoTributario.objects.filter(id_venta_origen=id_venta_origen)
        if not docs.exists():
            return Response(
                {"detail": f"No se encontró documento para la venta {id_venta_origen}."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = DocumentoTributarioSerializer(docs.order_by('-fecha_creacion'), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='reportes')
    def reportes(self, request):
        """Estadísticas de documentos tributarios emitidos."""
        docs = DocumentoTributario.objects.all()
        total_emisiones = docs.count()
        monto_total = docs.aggregate(total=Sum('monto_total'))['total'] or 0

        por_estado = []
        emitidos = 0
        rechazados = 0
        pendientes = 0
        for estado, label in DocumentoTributario.ESTADO_CHOICES:
            qs = docs.filter(estado=estado)
            cantidad = qs.count()
            por_estado.append({
                "estado": estado,
                "label": label,
                "cantidad": cantidad,
                "monto_total": float(qs.aggregate(total=Sum('monto_total'))['total'] or 0),
            })
            if estado == 'ACEPTADO':
                emitidos = cantidad
            elif estado in ('RECHAZADO', 'ERROR'):
                rechazados += cantidad
            elif estado in ('PENDIENTE', 'ENVIADO'):
                pendientes += cantidad

        return Response({
            "total_emisiones": total_emisiones,
            "emitidos": emitidos,
            "rechazados": rechazados,
            "pendientes": pendientes,
            "monto_total": float(monto_total),
            "estado_circuit_breaker": circuit_breaker.state,
            "por_estado": por_estado,
        })

    @action(detail=False, methods=['get'], url_path='estado-circuito')
    def estado_circuito(self, request):
        """Estado actual del Circuit Breaker."""
        return Response({
            "estado": circuit_breaker.state,
            "fallas_acumuladas": circuit_breaker.failures,
            "ultima_falla": circuit_breaker.last_failure_time,
            "remaining_wait": circuit_breaker.remaining_wait,
        })