from django.http import JsonResponse
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
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


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'notes']
    ordering_fields = ['created_at', 'amount', 'transaction_type']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            qs = Transaction.objects.all().select_related('business', 'category', 'created_by')
        else:
            qs = Transaction.objects.filter(
                business__owner=user
            ).select_related('business', 'category', 'created_by')

        # Filter by business if passed as ?business=X
        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        # Filter by type if passed as ?transaction_type=sale
        txn_type = self.request.query_params.get('transaction_type')
        if txn_type:
            qs = qs.filter(transaction_type=txn_type)

        # Filter by date if passed as ?date=2026-02-23
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(created_at__date=date)

        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# Keep old placeholder in case anything still references it
def transaction_list(request):
    return JsonResponse({"message": "Transactions endpoint working"})




class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            qs = Transaction.objects.all().select_related('business', 'category', 'created_by')
        else:
            qs = Transaction.objects.filter(
                business__owner=user
            ).select_related('business', 'category', 'created_by')

        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        txn_type = self.request.query_params.get('transaction_type')
        if txn_type:
            qs = qs.filter(transaction_type=txn_type)

        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(created_at__date=date)

        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        # ← TEMPORARY DEBUG: print exactly what's being received and rejected
        print("=== TRANSACTION POST DATA ===")
        print("DATA:", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("=== VALIDATION ERRORS ===")
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)