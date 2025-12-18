# chatbot/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.chat_view, name='ask_qwen'),
]