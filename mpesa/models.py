from django.db import models
from businesses.models import Business


class MpesaTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('success',  'Success'),
        ('failed',   'Failed'),
        ('timeout',  'Timeout'),
        ('cancelled','Cancelled'),
    ]

    # STK Push request fields
    business            = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='mpesa_transactions')
    phone_number        = models.CharField(max_length=15)
    amount              = models.DecimalField(max_digits=10, decimal_places=2)
    description         = models.CharField(max_length=200, blank=True, default='')
    account_reference   = models.CharField(max_length=100, blank=True, default='')

    # Safaricom response fields
    merchant_request_id = models.CharField(max_length=100, blank=True, default='')
    checkout_request_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Callback fields (filled after payment)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, default='')
    transaction_date     = models.CharField(max_length=30, blank=True, default='')
    result_code          = models.IntegerField(null=True, blank=True)
    result_desc          = models.CharField(max_length=200, blank=True, default='')

    # Linked sale transaction (created after successful payment)
    sale_transaction     = models.OneToOneField(
                               'transactions.Transaction',
                               null=True, blank=True,
                               on_delete=models.SET_NULL,
                               related_name='mpesa_payment'
                           )

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone_number} | KES {self.amount} | {self.status}'