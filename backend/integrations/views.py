import httpx
from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DocumentoTributario, LogConsulta
from .serializers import (
    VentaEmitirSerializer,
    DocumentoTributarioSerializer,
    LogConsultaSerializer,
)
from django.conf import settings

from core.circuit_breaker import CircuitBreaker

# Instancia global del Circuit Breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
)


class IntegracionViewSet(viewsets.ViewSet):
    """
    ViewSet principal para la integración con SimpleAPI (SII).
    Emite boletas, consulta estado y genera reportes.
    """

    def _get_credencial_activa(self):
        from credentials.models import CredencialSimpleAPI
        try:
            return CredencialSimpleAPI.objects.filter(activa=True).first()
        except CredencialSimpleAPI.DoesNotExist:
            return None

    def _call_simpleapi(self, payload, credencial):
        """Llama a SimpleAPI protegido por Circuit Breaker."""
        if not circuit_breaker.can_execute():
            raise Exception(
                "Circuit Breaker OPEN: SimpleAPI no está respondiendo. "
                "Inténtelo más tarde."
            )

        headers = {
            "Authorization": f"Bearer {credencial.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=settings.SIMPLEAPI_TIMEOUT) as client:
                response = client.post(
                    f"{credencial.base_url}/dte/emitir",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                circuit_breaker.record_success()
                return data
        except httpx.HTTPError as exc:
            circuit_breaker.record_failure()
            raise Exception(f"Error de conexión con SimpleAPI: {str(exc)}")

    def _build_sii_payload(self, id_venta, items, monto_total):
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
                        "QtyItem": item["cantidad"],
                        "PrcItem": float(item["precio_unitario"]),
                        "MontoItem": float(item["cantidad"]) * float(item["precio_unitario"])
                    }
                    for index, item in enumerate(items)
                ]
            }
        }

    @action(detail=False, methods=['post'], url_path='emitir-boleta')
    def emitir_boleta(self, request):
        """Emite una boleta electrónica vía SimpleAPI."""
        serializer = VentaEmitirSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        id_venta = data['id_venta']
        items = data['items']
        monto_total = sum(
            item['cantidad'] * float(item['precio_unitario'])
            for item in items
        )

        # Verificar que no exista ya una emisión para esta venta
        if DocumentoTributario.objects.filter(id_venta=id_venta).exists():
            return Response(
                {"detail": f"La venta {id_venta} ya tiene un documento tributario emitido."},
                status=status.HTTP_409_CONFLICT
            )

        credencial = self._get_credencial_activa()
        if not credencial:
            return Response(
                {"detail": "No hay credenciales activas de SimpleAPI configuradas."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        payload = self._build_sii_payload(id_venta, items, monto_total)

        try:
            resultado_sii = self._call_simpleapi(payload, credencial)
        except Exception as e:
            LogConsulta.objects.create(
                tipo_consulta='EMISION',
                id_venta_ref=id_venta,
                parametros={"items_count": len(items)},
                respuesta={"error": str(e)}
            )
            return Response(
                {"detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        folio = resultado_sii.get("folio")
        estado = resultado_sii.get("estado", "EMITIDO")

        doc = DocumentoTributario.objects.create(
            id_venta=id_venta,
            folio=folio,
            tipo_documento=39,
            estado=estado,
            respuesta_sii=resultado_sii,
            monto_total=monto_total,
        )

        LogConsulta.objects.create(
            tipo_consulta='EMISION',
            id_venta_ref=id_venta,
            parametros={"items_count": len(items), "monto_total": monto_total},
            respuesta={"folio": folio, "estado": estado}
        )

        return Response({
            "id_venta": id_venta,
            "folio": folio,
            "estado": estado,
            "monto_total": monto_total,
            "tipo_documento": 39,
            "message": "Boleta emitida correctamente",
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='consulta/(?P<id_venta>[^/.]+)')
    def consultar_venta(self, request, id_venta=None):
        """Consulta el estado de una venta por su ID."""
        try:
            doc = DocumentoTributario.objects.get(id_venta=id_venta)
            serializer = DocumentoTributarioSerializer(doc)
            return Response(serializer.data)
        except DocumentoTributario.DoesNotExist:
            return Response(
                {"detail": f"No se encontró documento para la venta {id_venta}."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='reportes')
    def reportes(self, request):
        """Estadísticas de documentos tributarios emitidos."""
        docs = DocumentoTributario.objects.all()
        total_emisiones = docs.count()
        emitidos = docs.filter(estado='EMITIDO').count()
        rechazados = docs.filter(estado='RECHAZADO').count()
        pendientes = docs.filter(estado='PENDIENTE').count()
        monto_total = docs.aggregate(total=Sum('monto_total'))['total'] or 0

        return Response({
            "total_emisiones": total_emisiones,
            "emitidos": emitidos,
            "rechazados": rechazados,
            "pendientes": pendientes,
            "monto_total": float(monto_total),
            "estado_circuit_breaker": circuit_breaker.state,
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
