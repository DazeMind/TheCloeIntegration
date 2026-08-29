from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IntegracionViewSet

router = DefaultRouter()
router.register(r'', IntegracionViewSet, basename='integracion')

urlpatterns = [
    path('', include(router.urls)),
]
