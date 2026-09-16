from rest_framework import viewsets
from .models import ConfiguracionEmpresa
from .serializers import ConfiguracionEmpresaSerializer


class ConfiguracionViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionEmpresa.objects.all()
    serializer_class = ConfiguracionEmpresaSerializer

    def get_queryset(self):
        # Solo configuración activa
        return self.queryset.filter(activa=True)

    def perform_create(self, serializer):
        empresa = serializer.validated_data.get('empresa')
        ambiente = serializer.validated_data.get('ambiente', 'testing')
        if empresa:
            ConfiguracionEmpresa.objects.filter(
                empresa=empresa, ambiente=ambiente, activa=True
            ).update(activa=False)
        serializer.save()