from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import BusinessViewSet, CustomerViewSet, SupplierViewSet

router = SimpleRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'', BusinessViewSet, basename='business')

urlpatterns = [
    path('', include(router.urls)),
]