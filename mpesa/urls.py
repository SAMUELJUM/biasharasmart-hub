from django.urls import path
from . import views

urlpatterns = [
    path('stk-push/',              views.stk_push,          name='mpesa-stk-push'),
    path('callback/',              views.mpesa_callback,    name='mpesa-callback'),
    path('status/<str:checkout_request_id>/', views.stk_status, name='mpesa-status'),
    path('transactions/',          views.mpesa_transactions, name='mpesa-transactions'),
]