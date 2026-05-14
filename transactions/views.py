from django.http import JsonResponse
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_filters import rest_framework as django_filters
from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Category.objects.all().select_related('business')
        return Category.objects.filter(business__owner=user)


# Add this filter class
class TransactionFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    date = django_filters.DateFilter(field_name='created_at', lookup_expr='date')

    class Meta:
        model = Transaction
        fields = {
            'transaction_type': ['exact'],
            'business': ['exact'],
            'created_at': ['date', 'date__gte', 'date__lte'],
        }


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TransactionFilter  # Use the filter class for advanced filtering
    search_fields = ['description', 'notes']
    ordering_fields = ['created_at', 'amount', 'transaction_type', 'date']
    ordering = ['-created_at']  # Default ordering

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            qs = Transaction.objects.all().select_related('business', 'category', 'created_by')
        else:
            qs = Transaction.objects.filter(
                business__owner=user
            ).select_related('business', 'category', 'created_by')

        # Manual filtering (optional - filterset_class handles this too)
        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)