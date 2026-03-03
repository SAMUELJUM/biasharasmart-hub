from django.urls import path, include
from rest_framework.routers import SimpleRouter
router = SimpleRouter()
from . import views

router = SimpleRouter()
router.register(r'forecasts', views.ForecastViewSet, basename='forecast')
router.register(r'credit-scores', views.CreditScoreViewSet, basename='creditscore')
router.register(r'alerts', views.AlertViewSet, basename='alert')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Custom endpoints
    path('dashboard/', views.analytics_dashboard, name='analytics-dashboard'),
    path('business-health/', views.business_health, name='business-health'),
    path('generate-report/', views.generate_report, name='generate-report'),
]