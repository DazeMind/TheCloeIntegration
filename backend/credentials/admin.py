from django.contrib import admin
from .models import CredencialSimpleAPI


@admin.register(CredencialSimpleAPI)
class CredencialSimpleAPIAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'api_key_masked', 'base_url', 'activa', 'fecha_creacion']
    list_filter = ['activa']
    search_fields = ['nombre']

    def api_key_masked(self, obj):
        if obj.api_key and len(obj.api_key) > 4:
            return obj.api_key[:2] + '*' * (len(obj.api_key) - 4)
        return obj.api_key
    api_key_masked.short_description = 'API Key'
