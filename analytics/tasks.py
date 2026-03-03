from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from businesses.models import Business
from .services import ForecastingService, CreditScoringService
from .models import Alert
from inventory.models import Product


@shared_task
def generate_all_forecasts():
    """Generate forecasts for all active businesses"""
    businesses = Business.objects.filter(is_active=True)

    for business in businesses:
        generate_business_forecast.delay(business.id)


@shared_task
def generate_business_forecast(business_id):
    """Generate forecast for a single business"""
    service = ForecastingService()
    service.forecast_sales_arima(business_id)


@shared_task
def calculate_all_credit_scores():
    """Calculate credit scores for all businesses"""
    businesses = Business.objects.filter(is_active=True)

    for business in businesses:
        calculate_business_credit_score.delay(business.id)


@shared_task
def calculate_business_credit_score(business_id):
    """Calculate credit score for a single business"""
    service = CreditScoringService()
    credit_score = service.calculate_credit_score(business_id)

    if credit_score and credit_score.score < 50:
        # Create alert for low credit score
        Alert.objects.create(
            business_id=business_id,
            alert_type='credit_score_change',
            severity='warning',
            title='Low Credit Score Alert',
            message=f'Your business credit score is {credit_score.score} ({credit_score.score_grade}). Consider improving your transaction consistency to access better loan terms.',
            suggested_action='Maintain daily transaction records and reduce cash flow volatility'
        )


@shared_task
def check_low_stock_alerts():
    """Check for low stock and create alerts"""
    low_stock_products = Product.objects.filter(
        current_quantity__lte=models.F('reorder_level'),
        is_active=True
    ).select_related('business')

    for product in low_stock_products:
        # Check if alert already exists and is not resolved
        existing_alert = Alert.objects.filter(
            business=product.business,
            related_product=product,
            alert_type='low_stock',
            is_resolved=False
        ).first()

        if not existing_alert:
            Alert.objects.create(
                business=product.business,
                alert_type='low_stock',
                severity='warning',
                title=f'Low Stock Alert: {product.name}',
                message=f'{product.name} is below reorder level. Current stock: {product.current_quantity} {product.unit}. Reorder level: {product.reorder_level} {product.unit}.',
                related_product=product,
                suggested_action=f'Consider reordering {max(product.reorder_level * 2, product.current_quantity * 3)} {product.unit} to maintain optimal stock levels.'
            )