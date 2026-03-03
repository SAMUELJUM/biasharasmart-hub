from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Business, StaffMember, Customer, Supplier
from .serializers import BusinessSerializer, StaffMemberSerializer, CustomerSerializer, SupplierSerializer


class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Business.objects.all().select_related('owner').order_by('-created_at')
        return Business.objects.filter(owner=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def add_staff(self, request, pk=None):
        business = self.get_object()
        if business.owner != request.user:
            return Response(
                {'error': 'Only business owner can add staff'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = StaffMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(business=business, added_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def staff_list(self, request, pk=None):
        business = self.get_object()
        staff = StaffMember.objects.filter(business=business, is_active=True)
        serializer = StaffMemberSerializer(staff, many=True)
        return Response(serializer.data)


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            qs = Customer.objects.all().select_related('business')
        else:
            qs = Customer.objects.filter(
                business__owner=user
            ).select_related('business')

        # Filter by business if passed as ?business=X
        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        return qs.order_by('-created_at')


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            qs = Supplier.objects.all().select_related('business')
        else:
            qs = Supplier.objects.filter(
                business__owner=user
            ).select_related('business')

        # Filter by business if passed as ?business=X
        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)

        return qs.order_by('-created_at')