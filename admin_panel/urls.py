from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from . import views

staff_required = staff_member_required(login_url='/login/')

urlpatterns = [
    # Dashboard
    path('', staff_required(views.admin_dashboard), name='admin-panel'),
    path('dashboard/', staff_required(views.admin_dashboard), name='admin-dashboard'),
    path('health/', views.admin_health_check, name='admin-health'),


    # User management
    path('users/', staff_required(views.admin_users), name='admin-users'),
    path('users/<int:user_id>/', staff_required(views.admin_user_detail), name='admin-user-detail'),

    # Business management
    path('businesses/', staff_required(views.admin_businesses), name='admin-businesses'),
    path('businesses/<int:business_id>/', staff_required(views.admin_business_detail), name='admin-business-detail'),

    # Transaction management
    path('transactions/', staff_required(views.admin_transactions), name='admin-transactions'),

    # Alert management
    path('alerts/', staff_required(views.admin_alerts), name='admin-alerts'),

    # Analytics
    path('analytics/', staff_required(views.admin_analytics), name='admin-analytics'),

    path('subscriptions/', views.admin_subscriptions, name='admin_subscriptions'),
    path('logs/', views.admin_logs, name='admin_logs'),

    path('customers/', views.customers_view, name='admin_customers'),
    path('suppliers/', views.suppliers_view, name='admin_suppliers'),
    path('pos/', views.pos_view, name='admin_pos'),

    # Settings
    path('settings/', staff_required(views.admin_settings), name='admin-settings'),

    # Logout
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='admin-logout'),
]