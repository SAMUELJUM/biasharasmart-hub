from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    #path('', views.integration_status, name='integration-status'),
    path('ussd/', views.ussd_callback, name='ussd'),
    path('whatsapp/', views.whatsapp_webhook, name='whatsapp'),
]
