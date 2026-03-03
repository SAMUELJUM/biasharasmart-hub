from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from businesses.models import Business
from transactions.models import Transaction, Category
from analytics.services import ForecastingService, CreditScoringService
from accounts.models import User


class ForecastingServiceTests(TestCase):
    def setUp(self):
        # Create test user and business
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='254712345678',
            password='testpass123'
        )
        self.business = Business.objects.create(
            owner=self.user,
            name='Test Business',
            sector='retail',
            county='Nairobi',
            town='CBD',
            phone_number='254712345678'
        )

        # Create some transactions
        category = Category.objects.create(
            business=self.business,
            name='Sales',
            category_type='income'
        )

        # Create 60 days of sales data
        for i in range(60):
            date = timezone.now().date() - timedelta(days=i)
            Transaction.objects.create(
                business=self.business,
                transaction_type='sale',
                category=category,
                amount=1000 + (i * 10),
                date=date,
                payment_mode='cash'
            )

    def test_prepare_time_series_data(self):
        service = ForecastingService()
        df = service.prepare_time_series_data(self.business.id, days=30)

        self.assertIsNotNone(df)
        self.assertEqual(len(df), 30)  # Should have 30 days of data

    def test_forecast_sales_arima(self):
        service = ForecastingService()
        forecasts = service.forecast_sales_arima(self.business.id, periods=7)

        self.assertIsNotNone(forecasts)
        self.assertEqual(len(forecasts), 7)

        # Check forecast values are positive
        for forecast in forecasts:
            self.assertGreater(forecast.predicted_value, 0)


class CreditScoringTests(TestCase):
    def setUp(self):
        # Similar setup as above
        pass

    def test_credit_score_calculation(self):
        service = CreditScoringService()
        score = service.calculate_credit_score(self.business.id)

        self.assertIsNotNone(score)
        self.assertTrue(0 <= score.score <= 100)
        self.assertIn(score.score_grade, ['A', 'B', 'C', 'D', 'E'])