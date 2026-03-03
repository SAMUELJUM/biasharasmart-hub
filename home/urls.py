from django.urls import path
from . import views
from accounts import views as account_views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/', views.api_root, name='api-root'),
    path('health/', views.health_check, name='health-check'),
    path('help/', views.help_page, name='help'),
    path('help/download/', views.download_user_guide, name='download-guide'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('chat/', account_views.chat_page, name='chat'),  # ← ADD
    path('chat/api/', account_views.chat_api, name='chat-api'),

]