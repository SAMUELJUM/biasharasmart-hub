from django.db import models
from django.conf import settings
from businesses.models import Business
from businesses.models import Customer, Supplier


class Category(models.Model):
    """Transaction categories"""
    CATEGORY_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        unique_together = ['business', 'name']

    def __str__(self):
        return f"{self.name} ({self.category_type})"


class Transaction(models.Model):
    """Financial transactions (sales and expenses)"""
    PAYMENT_MODES = (
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('card', 'Card'),
        ('other', 'Other'),
    )

    TRANSACTION_TYPES = (
        ('sale', 'Sale'),
        ('expense', 'Expense'),
        ('purchase', 'Purchase'),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES, default='cash')

    # For M-Pesa transactions
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    mpesa_phone = models.CharField(max_length=15, blank=True, null=True)

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # For offline sync
    sync_status = models.CharField(max_length=20, default='synced', choices=[
        ('pending', 'Pending Sync'),
        ('synced', 'Synced'),
        ('failed', 'Sync Failed'),
    ])
    device_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['business', 'date']),
            models.Index(fields=['business', 'transaction_type']),
            models.Index(fields=['sync_status']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} on {self.date}"

    customer = models.ForeignKey(
        'businesses.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transactions'
    )
    supplier = models.ForeignKey(
        'businesses.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transactions'
    )