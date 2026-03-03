from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import TransactionViewSet, CategoryViewSet

router = SimpleRouter()
router.register(r'', TransactionViewSet, basename='transactions')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
]