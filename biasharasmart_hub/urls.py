from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from businesses.views import CustomerViewSet, SupplierViewSet
from rest_framework.routers import DefaultRouter
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from accounts import views as accounts_views
from accounts.views import settings_page
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView



admin.site.site_url = '/admin-panel/'

urlpatterns = [
    # Home landing page
    path('', include('home.urls')),

    # HTML pages (user-facing)
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    path('login/', accounts_views.login_page, name='login'),
    path('register/', accounts_views.register_page, name='register'),
    path('verify-otp/', accounts_views.verify_otp_page, name='verify-otp'),
    path('dashboard/', accounts_views.dashboard_page, name='dashboard'),
    path('add-sale/', accounts_views.add_sale_page, name='add-sale'),
    path('add-expense/', accounts_views.add_expense_page, name='add-expense'),
    path('inventory/', accounts_views.inventory_page, name='inventory'),
    path('inventory/',     accounts_views.inventory_page,     name='inventory'),
    path('transactions/',  accounts_views.transactions_page,  name='transactions'),
    path('analytics/',     accounts_views.analytics_page,     name='analytics'),
    path('reports/',       accounts_views.reports_page,       name='reports'),
    path('alerts/',        accounts_views.alerts_page,        name='alerts'),
    path('business/',      accounts_views.business_page,      name='business'),
    path("settings/", settings_page, name="settings"),
    path('api/mpesa/', include('mpesa.urls')),
    path('integrations/', include('integrations.urls')),

    path('about/', TemplateView.as_view(template_name='accounts/about.html'), name='about'),
    path('blog/', TemplateView.as_view(template_name='accounts/blog.html'), name='blog'),
    path('careers/', TemplateView.as_view(template_name='accounts/careers.html'), name='careers'),
    path('privacy-policy/', TemplateView.as_view(template_name='accounts/privacy-policy.html'), name='privacy-policy'),
    path('terms-of-service/', TemplateView.as_view(template_name='accounts/terms-of-service.html'),
         name='terms-of-service'),
    path('cookie-policy/', TemplateView.as_view(template_name='accounts/cookie-policy.html'), name='cookie-policy'),
    path('data-protection/', TemplateView.as_view(template_name='accounts/data-protection.html'),
         name='data-protection'),
    path('terms/', TemplateView.as_view(template_name='accounts/terms.html'), name='terms'),
    path('contact-support/', TemplateView.as_view(template_name='accounts/contact_support.html'), name='contact-support'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # Admin
    path('admin/', admin.site.urls),
    path('admin-panel/', include('admin_panel.urls')),

    # API endpoints
    path('api/auth/', include('accounts.urls')),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/businesses/', include('businesses.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/reports/', include('reports.urls')),


# Password reset flow
    path('forgot-password/', accounts_views.forgot_password_page, name='forgot-password'),
    path('reset-otp/',       accounts_views.reset_otp_page,       name='reset-otp'),
    path('reset-password/',  accounts_views.reset_password_page,  name='reset-password'),


]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)