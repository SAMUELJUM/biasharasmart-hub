from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    # Coerce decimals to numbers so frontend integers are accepted
    current_quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    cost_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False,
        required=False, allow_null=True, default=0
    )
    reorder_level = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False,
        required=False, default=5
    )

    class Meta:
        model = Product
        fields = [
            'id', 'business', 'name', 'sku', 'barcode',
            'description', 'unit_price', 'cost_price',
            'current_quantity', 'reorder_level', 'maximum_level',
            'unit', 'supplier_name', 'supplier_contact',
            'is_active', 'created_at', 'updated_at',
        ]