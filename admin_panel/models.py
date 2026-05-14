from django.db import models


class Business(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ]

    TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('reorder_suggestion', 'Reorder Suggestion'),
        ('cashflow_warning', 'Cash Flow Warning'),
        ('payment_due', 'Payment Due'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='alerts')

    title = models.CharField(max_length=255)
    message = models.TextField()

    alert_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)

    suggested_action = models.CharField(max_length=255, blank=True, null=True)

    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.business.name}"