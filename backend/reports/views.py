from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from integrations.models import DocumentoTributario, LogConsulta
from .serializers import ResumenReporteSerializer, EstadoDocumentoSerializer


class ReporteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Resumen ejecutivo de la integración."""
        docs = DocumentoTributario.objects.all()
        total = docs.count()
        emitidos = docs.filter(estado='EMITIDO').count()
        rechazados = docs.filter(estado='RECHAZADO').count()
        pendientes = docs.filter(estado='PENDIENTE').count()
        monto_total = docs.aggregate(total=Sum('monto_total'))['total'] or 0
        tasa_exito = float(emitidos) / float(total) * 100 if total > 0 else 0.0

        from django.utils import timezone
        desde_hoy = timezone.now() - timezone.timedelta(days=7)
        ultimos_7 = docs.filter(fecha_creacion__gte=desde_hoy).count()
        desde_30 = timezone.now() - timezone.timedelta(days=30)
        ultimos_30 = docs.filter(fecha_creacion__gte=desde_30).count()

        return Response({
            "total_emisiones": total,
            "emitidos": emitidos,
            "rechazados": rechazados,
            "pendientes": pendientes,
            "monto_total": float(monto_total),
            "tasa_exito": round(tasa_exito, 2),
            "ultimos_7_dias": ultimos_7,
            "ultimos_30_dias": ultimos_30,
        })

    @action(detail=False, methods=['get'])
    def por_estado(self, request):
        """Documentos agrupados por estado."""
        docs = DocumentoTributario.objects.all()
        estados = []
        for estado, label in [('EMITIDO', 'Emitido'), ('RECHAZADO', 'Rechazado'), ('PENDIENTE', 'Pendiente')]:
            qs = docs.filter(estado=estado)
            estados.append({
                "estado": estado,
                "cantidad": qs.count(),
                "monto_total": float(qs.aggregate(total=Sum('monto_total'))['total'] or 0),
            })
        return Response({"estados": estados})

    @action(detail=False, methods=['get'])
    def historial(self, request):
        """Últimos documentos emitidos."""
        limit = int(request.query_params.get('limit', 20))
        docs = DocumentoTributario.objects.all()[:limit]
        from integrations.serializers import DocumentoTributarioSerializer
        serializer = DocumentoTributarioSerializer(docs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def logs(self, request):
        """Logs de consultas realizadas."""
        limit = int(request.query_params.get('limit', 50))
        logs = LogConsulta.objects.all()[:limit]
        from integrations.serializers import LogConsultaSerializer
        serializer = LogConsultaSerializer(logs, many=True)
        return Response(serializer.data)
