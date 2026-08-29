from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/integraciones/', include('integrations.urls')),
    path('api/v1/credenciales/', include('credentials.urls')),
    path('api/v1/configuracion/', include('configurations.urls')),
    path('api/v1/reportes/', include('reports.urls')),
]
