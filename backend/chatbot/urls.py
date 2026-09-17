from django.urls import path

from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.index, name='index'),
    path('widget/', views.widget, name='widget'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/reset/', views.reset_chat, name='reset_chat'),
]