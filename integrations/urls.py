from django.urls import path
from . import views

urlpatterns = [
    path('', views.integration_status, name='integration-status'),
]
