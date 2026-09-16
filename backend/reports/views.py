from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Sum
from django.utils import timezone

from integrations.models import DocumentoTributario, LogConsultaAPI


class ReporteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Resumen ejecutivo de la integración."""
        docs = DocumentoTributario.objects.all()
        total = docs.count()
        aceptados = docs.filter(estado='ACEPTADO').count()
        rechazados = docs.filter(estado='RECHAZADO').count()
        errores = docs.filter(estado='ERROR').count()
        pendientes = docs.filter(estado__in=['PENDIENTE', 'ENVIADO']).count()
        emitidos = aceptados
        monto_total = docs.aggregate(total=Sum('monto_total'))['total'] or 0
        tasa_exito = float(emitidos) / float(total) * 100 if total > 0 else 0.0

        desde_hoy = timezone.now() - timezone.timedelta(days=7)
        ultimos_7 = docs.filter(fecha_creacion__gte=desde_hoy).count()
        desde_30 = timezone.now() - timezone.timedelta(days=30)
        ultimos_30 = docs.filter(fecha_creacion__gte=desde_30).count()

        return Response({
            "total_emisiones": total,
            "emitidos": emitidos,
            "rechazados": rechazados + errores,
            "errores": errores,
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
        for estado, label in DocumentoTributario.ESTADO_CHOICES:
            qs = docs.filter(estado=estado)
            estados.append({
                "estado": estado,
                "label": label,
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
        logs = LogConsultaAPI.objects.all()[:limit]
        data = [{
            "endpoint": l.endpoint,
            "metodo_http": l.metodo_http,
            "codigo_respuesta_http": l.codigo_respuesta_http,
            "duracion_ms": l.duracion_ms,
            "mensaje_error": l.mensaje_error,
            "fecha_consulta": l.fecha_consulta,
        } for l in logs]
        return Response(data)