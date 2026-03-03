from django.urls import path
from . import views
from .views import settings_page
from .views import AdminUserListView, AdminUserDetailView

urlpatterns = [
    # API endpoints
    path('register/', views.UserRegistrationView.as_view(), name='api-register'),
    path('login/', views.UserLoginView.as_view(), name='api-login'),
    path('verify-otp/', views.OTPVerificationView.as_view(), name='api-verify-otp'),
    path('profile/', views.UserProfileView.as_view(), name='api-profile'),
    path("settings/", settings_page, name="settings"),
    path('resend-otp/', views.ResendOTPView.as_view(), name='api-resend-otp'),
    path('users/', AdminUserListView.as_view(), name='admin-users'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('users/<int:pk>/subscription/', views.UpdateSubscriptionView.as_view(), name='update-subscription'),
    path('logs/', views.logs_list, name='logs-list'),
    path('debug/', views.chat_debug, name='chat_debug'),
    # Authentication
    path('logout/', views.logout_view, name='logout'),
]