from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CredencialViewSet

router = DefaultRouter()
router.register(r'', CredencialViewSet, basename='credencial')

urlpatterns = [
    path('', include(router.urls)),
]
