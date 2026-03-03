from rest_framework import serializers
from .models import Business, StaffMember, Customer, Supplier


class BusinessSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        return '—'

    class Meta:
        model = Business
        fields = [
            'id', 'owner', 'owner_name', 'name', 'registration_number',
            'sector', 'county', 'town', 'location_description',
            'phone_number', 'email', 'mpesa_till_number', 'mpesa_paybill',
            'mpesa_account_number', 'date_established', 'employee_count',
            'monthly_revenue_estimate', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ('owner', 'owner_name', 'created_at', 'updated_at')  # ← FIXED


class StaffMemberSerializer(serializers.ModelSerializer):
    user_phone = serializers.ReadOnlyField(source='user.phone_number')
    user_name  = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = StaffMember
        fields = '__all__'
        read_only_fields = ('added_by', 'created_at')


class CustomerSerializer(serializers.ModelSerializer):
    full_name         = serializers.ReadOnlyField()
    total_spent       = serializers.ReadOnlyField()
    transaction_count = serializers.ReadOnlyField()

    class Meta:
        model  = Customer
        fields = [
            'id', 'business', 'first_name', 'last_name', 'full_name',
            'phone_number', 'email', 'location', 'notes', 'is_active',
            'total_spent', 'transaction_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class SupplierSerializer(serializers.ModelSerializer):
    total_purchases  = serializers.ReadOnlyField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model  = Supplier
        fields = [
            'id', 'business', 'name', 'contact_person', 'phone_number',
            'email', 'address', 'category', 'category_display', 'notes',
            'is_active', 'total_purchases', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']