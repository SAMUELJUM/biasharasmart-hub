from rest_framework import serializers
from .models import Category, Transaction
import datetime

try:
    from businesses.models import StaffMember
except ImportError:
    StaffMember = None


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('business', 'created_at')


class TransactionSerializer(serializers.ModelSerializer):
    category_name   = serializers.ReadOnlyField(source='category.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    business_name   = serializers.SerializerMethodField()
    date = serializers.DateField(required=False, default=datetime.date.today)

    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )

    def get_business_name(self, obj):
        return obj.business.name if obj.business else '—'

    class Meta:
        model = Transaction
        fields = [
            'id', 'business', 'business_name',
            'transaction_type', 'category', 'category_name',
            'amount', 'date', 'description',
            'payment_mode',                        # ← correct field name
            'mpesa_receipt', 'mpesa_phone',
            'customer', 'supplier',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
            'sync_status', 'device_id',
        ]
        read_only_fields = ('created_by', 'created_at', 'updated_at', 'sync_status')

    def validate(self, data):
        request = self.context.get('request')
        if not request:
            return data

        user = request.user

        # Superadmins and staff bypass all ownership checks
        if user.is_superuser or user.is_staff:
            return data

        business = data.get('business')
        if not business:
            return data

        # Owner of the business — allow
        if business.owner == user:
            return data

        # Check staff member permissions
        if StaffMember:
            try:
                is_staff = StaffMember.objects.filter(
                    business=business,
                    user=user,
                    permission_level__in=['add_transactions', 'full_access'],
                    is_active=True
                ).exists()
            except Exception:
                is_staff = False
        else:
            is_staff = False

        if not is_staff:
            raise serializers.ValidationError(
                "You don't have permission to add transactions to this business."
            )

        return data

    def create(self, validated_data):
        # Auto-assign created_by to the requesting user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)