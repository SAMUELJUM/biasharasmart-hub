from django.http import JsonResponse
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import Product
from .serializers import ProductSerializer

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product
from .serializers import ProductSerializer




class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'sku', 'barcode']
    ordering_fields = ['name', 'created_at', 'unit_price']

    def get_queryset(self):
        user = self.request.user

        # Admins see all products
        if user.is_staff or user.is_superuser:
            qs = Product.objects.all().select_related('business')
        else:
            # Regular users only see their own business products
            qs = Product.objects.filter(
                business__owner=user
            ).select_related('business')

        # Filter by business ID if passed as ?business=X
        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        # Only active products by default unless ?all=true
        if self.request.query_params.get('all') != 'true':
            qs = qs.filter(is_active=True)

        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save()


# Keep old function in case anything still references it
def inventory_list(request):
    return JsonResponse({"message": "Inventory endpoint working"})




class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            qs = Product.objects.all().select_related('business')
        else:
            qs = Product.objects.filter(business__owner=user).select_related('business')

        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        if self.request.query_params.get('all') != 'true':
            qs = qs.filter(is_active=True)

        return qs.order_by('name')

    def create(self, request, *args, **kwargs):
        print("=== INVENTORY POST DATA ===")
        print("DATA:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("=== VALIDATION ERRORS ===")
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)