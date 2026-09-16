import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_q.tasks import async_task
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from configurations.models import Empresa
from integrations.models import AgenteIntegracion, LogConsultaAPI
from .models import DetalleVenta, Venta
from .serializers import SaleCreateSerializer, SaleSerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class SaleViewSet(viewsets.ViewSet):
    """
    API pública de ventas consumida por el sitio privado 'DeCloé'.
    FASE 1: recepción, almacenamiento y consulta.
    FASE 2: la venta se encola en django-q al crearse y un worker emite el
    DTE (boleta/factura) en SimpleFactura de forma asíncrona.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _get_agente_decloe():
        agente, _ = AgenteIntegracion.objects.get_or_create(
            nombre='DECLOE',
            defaults={
                'tipo': 'SISTEMA',
                'descripcion': 'Agente del sistema privado DeCloé',
            },
        )
        return agente

    @staticmethod
    def _client_ip(request):
        return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() \
            or request.META.get("REMOTE_ADDR")

    def _get_venta(self, pk):
        try:
            return Venta.objects.get(pk=pk)
        except (Venta.DoesNotExist, TypeError, ValueError):
            return None

    def create(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        venta_existente = Venta.objects.filter(sale_id=data['sale_id']).first()
        if venta_existente:
            response_data = SaleSerializer(venta_existente).data
            response_data['message'] = "Sale already exists, returning existing record"
            return Response(response_data, status=status.HTTP_200_OK)

        empresa = Empresa.objects.filter(activa=True).first()
        if empresa is None:
            return Response(
                {"detail": "No active company configured to record the sale."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agente = self._get_agente_decloe()

        customer = data.get('customer') or {}
        monto_total = sum(
            (item['quantity'] * item['unit_price']) - item['discount']
            for item in data['items']
        )

        venta = Venta.objects.create(
            sale_id=data['sale_id'],
            document_type=data['document_type'],
            issued_at=data['issued_at'],
            payment_method=data.get('payment_method', 'CASH'),
            status='RECEIVED',
            monto_total=monto_total,
            empresa=empresa,
            cliente_rut=(str(customer.get('rut') or '').strip())[:12] or None,
            cliente_nombre=(str(customer.get('name') or '').strip())[:200] or None,
            cliente_direccion=(str(customer.get('address') or '').strip())[:250] or None,
            cliente_comuna=(str(customer.get('commune') or '').strip())[:100] or None,
            cliente_ciudad=(str(customer.get('city') or '').strip())[:100] or None,
        )

        for index, item in enumerate(data['items'], start=1):
            DetalleVenta.objects.create(
                venta=venta,
                linea=index,
                codigo_producto=(str(item.get('code') or '').strip())[:50] or None,
                nombre_producto=item['description'],
                cantidad=item['quantity'],
                precio_unitario=item['unit_price'],
                descuento=item['discount'],
                impuesto=item.get('tax', 'IVA'),
            )

        # FASE 2: encolar la emisión del DTE. Si el broker no está disponible la
        # venta queda RECEIVED y se puede reprocesar con procesar_ventas_pendientes.
        try:
            async_task(
                'sales.tasks.procesar_venta',
                venta.pk,
                timeout=120,
            )
            venta.status = 'QUEUED'
            venta.save(update_fields=['status', 'fecha_actualizacion'])
        except Exception as exc:
            logger.warning(
                'No se pudo encolar la venta %s (%s): %s',
                venta.sale_id, venta.pk, exc,
            )

        LogConsultaAPI.objects.create(
            agente=agente,
            endpoint='/api/v1/sales/',
            metodo_http='POST',
            codigo_respuesta_http=status.HTTP_202_ACCEPTED,
            payload_enviado=request.data,
            ip_origen=self._client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )

        # El response conserva el contrato aprobado en FASE 1 (status RECEIVED);
        # el estado interno real queda en 'QUEUED' y se consulta por GET.
        return Response({
            "sale_id": venta.id,
            "reference": venta.sale_id,
            "status": "RECEIVED",
            "message": "Sale received and queued for processing",
        }, status=status.HTTP_202_ACCEPTED)

    def retrieve(self, request, pk=None):
        venta = self._get_venta(pk)
        if venta is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SaleSerializer(venta).data)

    @action(detail=True, methods=['get'], url_path='document')
    def document(self, request, pk=None):
        venta = self._get_venta(pk)
        if venta is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = SaleSerializer(venta).data
        if data['document'] is None:
            return Response(
                {"error": "Document not available yet"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data['document'])