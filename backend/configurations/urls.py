from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConfiguracionViewSet

router = DefaultRouter()
router.register(r'', ConfiguracionViewSet, basename='configuracion')

urlpatterns = [
    path('', include(router.urls)),
]
