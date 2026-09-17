from django.db import models


class ChatbotSession(models.Model):
    """Modelo para tracking de sesiones en Django Admin.
    Permite testing del chatbot desde la interfaz de admin.
    """
    session_id = models.CharField(max_length=40, unique=True, help_text="ID único de la sesión del chatbot")
    created_at = models.DateTimeField(auto_now_add=True)
    message_count = models.IntegerField(default=0, help_text="Cantidad total de mensajes en la sesión")
    last_message = models.TextField(blank=True, help_text="Último mensaje recibido")
    last_response = models.TextField(blank=True, help_text="Última respuesta del bot")

    class Meta:
        verbose_name = "Sesión Chatbot"
        verbose_name_plural = "Sesiones Chatbot"
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id[:8]}..."

    def increment_message(self):
        """Incrementa contador de mensajes y actualiza último mensaje."""
        self.message_count += 1
        self.save(update_fields=['message_count', 'last_message'])