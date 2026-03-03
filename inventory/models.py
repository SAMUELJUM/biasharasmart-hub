from django.db import models
from django.conf import settings
from businesses.models import Business


class Product(models.Model):
    """Products in inventory"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True)

    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Stock levels
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Unit of measure
    UNIT_CHOICES = (
        ('pieces', 'Pieces'),
        ('kg', 'Kilograms'),
        ('liters', 'Liters'),
        ('meters', 'Meters'),
        ('boxes', 'Boxes'),
        ('dozens', 'Dozens'),
        ('other', 'Other'),
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pieces')

    # Supplier info
    supplier_name = models.CharField(max_length=200, blank=True, null=True)
    supplier_contact = models.CharField(max_length=50, blank=True, null=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['business', 'name']
        indexes = [
            models.Index(fields=['business', 'is_active']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f"{self.name} - {self.current_quantity} {self.unit}"

    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.current_quantity <= self.reorder_level


class StockMovement(models.Model):
    """Track stock movements (in/out)"""
    MOVEMENT_TYPES = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    previous_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    new_quantity = models.DecimalField(max_digits=10, decimal_places=2)

    # Optional reference to transaction
    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.SET_NULL, null=True, blank=True)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pk:  # New movement
            product = Product.objects.get(pk=self.product_id)
            self.previous_quantity = product.current_quantity

            if self.movement_type == 'in':
                self.new_quantity = self.previous_quantity + self.quantity
            elif self.movement_type == 'out':
                self.new_quantity = self.previous_quantity - self.quantity
            else:  # adjustment or return
                self.new_quantity = self.quantity

            # Update product quantity
            product.current_quantity = self.new_quantity
            product.save()

        super().save(*args, **kwargs)