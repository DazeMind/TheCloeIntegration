from rest_framework import viewsets
from .models import ConfiguracionIntegracion
from .serializers import ConfiguracionIntegracionSerializer


class ConfiguracionViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionIntegracion.objects.all()
    serializer_class = ConfiguracionIntegracionSerializer

    def get_queryset(self):
        # Solo una configuración activa
        return self.queryset.filter(activa=True)

    def perform_create(self, serializer):
        # Desactivar cualquier configuración previa activa
        ConfiguracionIntegracion.objects.filter(activa=True).update(activa=False)
        serializer.save()
