from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ProductViewSet

router = SimpleRouter()
router.register(r'', ProductViewSet, basename='inventory')

urlpatterns = [
    path('', include(router.urls)),
]