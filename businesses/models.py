from django.db import models
from django.db import models
from django.conf import settings


class Business(models.Model):
    """Business profile model"""
    SECTOR_CHOICES = (
        ('retail', 'Retail'),
        ('manufacturing', 'Manufacturing'),
        ('agriculture', 'Agriculture'),
        ('services', 'Services'),
        ('transport', 'Transport'),
        ('construction', 'Construction'),
        ('technology', 'Technology'),
        ('other', 'Other'),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='businesses')
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    sector = models.CharField(max_length=50, choices=SECTOR_CHOICES)
    county = models.CharField(max_length=100)
    town = models.CharField(max_length=100)
    location_description = models.TextField(blank=True)

    # Contact information
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)

    # M-Pesa details
    mpesa_till_number = models.CharField(max_length=20, blank=True, null=True)
    mpesa_paybill = models.CharField(max_length=20, blank=True, null=True)
    mpesa_account_number = models.CharField(max_length=50, blank=True, null=True)

    # Business details
    date_established = models.DateField(null=True, blank=True)
    employee_count = models.IntegerField(default=1)
    monthly_revenue_estimate = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'businesses'
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['county', 'sector']),
        ]

    def __str__(self):
        return f"{self.name} - {self.owner.phone_number}"


class StaffMember(models.Model):
    """Staff members with limited access to a business"""
    PERMISSION_LEVELS = (
        ('view_only', 'View Only'),
        ('add_transactions', 'Add Transactions'),
        ('full_access', 'Full Access'),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_businesses')
    permission_level = models.CharField(max_length=20, choices=PERMISSION_LEVELS, default='add_transactions')
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name='added_staff')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['business', 'user']


class Customer(models.Model):
    business     = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='customers')
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email        = models.EmailField(blank=True, null=True)
    location     = models.CharField(max_length=200, blank=True)
    notes        = models.TextField(blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.phone_number}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def total_spent(self):
        from transactions.models import Transaction
        total = Transaction.objects.filter(
            business=self.business,
            customer=self,
            transaction_type='sale'
        ).aggregate(total=models.Sum('amount'))['total']
        return float(total or 0)

    @property
    def transaction_count(self):
        from transactions.models import Transaction
        return Transaction.objects.filter(
            business=self.business,
            customer=self
        ).count()


class Supplier(models.Model):
    CATEGORY_CHOICES = [
        ('goods', 'Goods'),
        ('services', 'Services'),
        ('raw_materials', 'Raw Materials'),
        ('equipment', 'Equipment'),
        ('other', 'Other'),
    ]

    business       = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='suppliers')
    name           = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone_number   = models.CharField(max_length=20)
    email          = models.EmailField(blank=True, null=True)
    address        = models.CharField(max_length=300, blank=True)
    category       = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='goods')
    notes          = models.TextField(blank=True)
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    @property
    def total_purchases(self):
        from transactions.models import Transaction
        total = Transaction.objects.filter(
            business=self.business,
            supplier=self,
            transaction_type='expense'
        ).aggregate(total=models.Sum('amount'))['total']
        return float(total or 0)

