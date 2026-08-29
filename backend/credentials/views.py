from rest_framework import viewsets
from .models import CredencialSimpleAPI
from .serializers import CredencialSimpleAPISerializer


class CredencialViewSet(viewsets.ModelViewSet):
    queryset = CredencialSimpleAPI.objects.all()
    serializer_class = CredencialSimpleAPISerializer

    def perform_create(self, serializer):
        serializer.save()
