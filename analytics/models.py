from django.db import models
from businesses.models import Business


class Forecast(models.Model):
    """AI-generated forecasts"""
    FORECAST_TYPES = (
        ('sales', 'Sales Forecast'),
        ('expenses', 'Expenses Forecast'),
        ('cashflow', 'Cash Flow Forecast'),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='forecasts')
    forecast_type = models.CharField(max_length=10, choices=FORECAST_TYPES)
    forecast_date = models.DateField()  # The date this forecast is for
    predicted_value = models.DecimalField(max_digits=15, decimal_places=2)
    lower_bound = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    upper_bound = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    confidence_level = models.FloatField(default=0.95)  # 95% confidence interval

    # Model metadata
    model_used = models.CharField(max_length=50)  # ARIMA, Prophet, etc.
    training_data_points = models.IntegerField()
    accuracy_metric = models.FloatField(null=True, blank=True)  # MAPE, RMSE etc.

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-forecast_date', '-created_at']
        indexes = [
            models.Index(fields=['business', 'forecast_type', 'forecast_date']),
        ]


class CreditScore(models.Model):
    """Credit scoring for businesses"""
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='credit_score')
    score = models.IntegerField()  # 0-100
    score_grade = models.CharField(max_length=2, choices=[
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor'),
        ('E', 'E - Very Poor'),
    ])

    # Score components
    transaction_consistency = models.FloatField()  # 0-1
    average_balance = models.DecimalField(max_digits=15, decimal_places=2)
    months_of_history = models.IntegerField()
    repayment_history_score = models.FloatField(null=True, blank=True)

    # Metadata
    last_calculated = models.DateTimeField(auto_now=True)
    calculation_version = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.business.name}: {self.score} ({self.score_grade})"


class Alert(models.Model):
    """System-generated alerts"""
    ALERT_TYPES = (
        ('low_stock', 'Low Stock'),
        ('cashflow_warning', 'Cash Flow Warning'),
        ('forecast_update', 'Forecast Update'),
        ('credit_score_change', 'Credit Score Change'),
        ('reorder_suggestion', 'Reorder Suggestion'),
        ('payment_due', 'Payment Due'),
    )

    SEVERITY_LEVELS = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()

    # Related data
    related_product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True, blank=True)
    suggested_action = models.TextField(blank=True)
    action_data = models.JSONField(default=dict)  # Store action parameters

    # Status
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'is_read', 'is_resolved']),
            models.Index(fields=['alert_type', 'severity']),
        ]