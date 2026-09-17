from django.conf import settings
from django.contrib import admin
from django.urls import path, reverse
from django.template.response import TemplateResponse

from .models import ChatbotSession


@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
    """Interfaz de admin para testing y monitoring del chatbot."""

    # Template del changelist con boton de acceso al playground
    change_list_template = 'chatbot/admin_changelist_playground_button.html'

    list_display = (
        'session_id_short',
        'created_at',
        'message_count',
        'last_message_preview',
    )
    list_filter = ('created_at',)
    search_fields = ('session_id',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def get_urls(self):
        """Agrega la ruta del playground de pruebas, protegida por el admin."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'playground/',
                self.admin_site.admin_view(self.playground_view),
                name='chatbot_playground',
            ),
        ]
        return custom_urls + urls

    def playground_view(self, request):
        """Caja de pruebas: embed del widget real via iframe (mismo origen)."""
        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Playground Chatbot',
            'opts': self.model._meta,
            'widget_url': reverse('chatbot:widget'),
            'changelist_url': reverse(
                'admin:chatbot_chatbotsession_changelist'
            ),
            'GEMINI_MODEL': settings.GEMINI_MODEL,
        })
        return TemplateResponse(
            request, 'chatbot/admin_playground.html', context
        )

    def session_id_short(self, obj):
        """Muestra solo los primeros y últimos 8 caracteres del session_id."""
        return f"{obj.session_id[:8]}...{obj.session_id[-8:]}"
    session_id_short.short_description = 'ID Sesión'
    session_id_short.admin_order_field = 'session_id'

    def last_message_preview(self, obj):
        """Vista previa del último mensaje (máx 50 chars)."""
        return obj.last_message[:50] + "..." if obj.last_message else "-"
    last_message_preview.short_description = 'Último mensaje'
    last_message_preview.admin_order_field = 'last_message'

    def get_queryset(self, request):
        """Optimiza query con select_related si es necesario."""
        return super().get_queryset(request).select_related()