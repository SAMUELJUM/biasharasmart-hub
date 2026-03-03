import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from django.db.models import Sum, Avg
from transactions.models import Transaction
from inventory.models import Product
from .models import Forecast, CreditScore, Alert


class ForecastingService:
    """Service for time-series forecasting"""

    @staticmethod
    def prepare_time_series_data(business_id, days=90):
        """Prepare transaction data for forecasting"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Get daily sales
        daily_sales = Transaction.objects.filter(
            business_id=business_id,
            transaction_type='sale',
            date__gte=start_date,
            date__lte=end_date
        ).values('date').annotate(
            total=Sum('amount')
        ).order_by('date')

        # Create DataFrame with all dates
        df = pd.DataFrame(list(daily_sales))
        if df.empty:
            return None

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Resample to daily frequency and fill missing
        df = df.resample('D').sum()
        df['total'] = df['total'].fillna(0)

        return df

    @staticmethod
    def forecast_sales_arima(business_id, periods=30):
        """Forecast sales using ARIMA"""
        df = ForecastingService.prepare_time_series_data(business_id)
        if df is None or len(df) < 30:
            return None

        try:
            # Fit ARIMA model
            model = ARIMA(df['total'], order=(5, 1, 0))
            model_fit = model.fit()

            # Make forecast
            forecast = model_fit.forecast(steps=periods)
            forecast_index = pd.date_range(
                start=df.index[-1] + timedelta(days=1),
                periods=periods,
                freq='D'
            )

            # Create forecast records
            forecasts = []
            for date, value in zip(forecast_index, forecast):
                forecast_record = Forecast(
                    business_id=business_id,
                    forecast_type='sales',
                    forecast_date=date.date(),
                    predicted_value=value,
                    model_used='ARIMA',
                    training_data_points=len(df),
                    accuracy_metric=0.85  # Placeholder - calculate actual MAPE
                )
                forecasts.append(forecast_record)

            # Bulk create forecasts
            Forecast.objects.bulk_create(forecasts)

            return forecasts

        except Exception as e:
            print(f"Forecasting error: {e}")
            return None

    @staticmethod
    def detect_anomalies(business_id):
        """Detect anomalies in transaction patterns"""
        df = ForecastingService.prepare_time_series_data(business_id, days=30)
        if df is None or len(df) < 7:
            return []

        # Simple anomaly detection using z-score
        mean = df['total'].mean()
        std = df['total'].std()

        anomalies = []
        for date, row in df.iterrows():
            z_score = (row['total'] - mean) / (std + 0.001)
            if abs(z_score) > 3:  # More than 3 std deviations
                anomalies.append({
                    'date': date.date(),
                    'amount': row['total'],
                    'z_score': z_score,
                    'type': 'high' if z_score > 0 else 'low'
                })

        return anomalies


class CreditScoringService:
    """Service for credit scoring"""

    @staticmethod
    def calculate_credit_score(business_id):
        """Calculate credit score for a business"""
        business = Business.objects.get(id=business_id)

        # Get transaction data
        transactions = Transaction.objects.filter(business=business)

        if transactions.count() < 10:
            return None  # Not enough data

        # Calculate metrics
        total_months = (datetime.now().date() -
                        transactions.earliest('date').date()).days / 30

        # Transaction consistency (daily transaction count)
        daily_counts = transactions.values('date').annotate(
            count=models.Count('id')
        ).order_by('date')

        if daily_counts:
            consistency = len([d for d in daily_counts if d['count'] > 0]) / max(total_months * 30, 1)
        else:
            consistency = 0

        # Average daily sales
        avg_daily_sales = transactions.filter(
            transaction_type='sale'
        ).aggregate(avg=Avg('amount'))['avg'] or 0

        # Cash flow stability (standard deviation of daily net)
        from django.db.models import Sum
        daily_net = transactions.values('date').annotate(
            net=Sum('amount', filter=models.Q(transaction_type='sale')) -
                Sum('amount', filter=models.Q(transaction_type='expense'))
        ).order_by('date')

        if daily_net:
            net_values = [d['net'] or 0 for d in daily_net]
            stability = 1 - (np.std(net_values) / (np.mean(net_values) + 0.001))
            stability = max(0, min(1, stability))
        else:
            stability = 0.5

        # Calculate final score (0-100)
        score = int(
            consistency * 30 +  # 30% weight
            stability * 30 +  # 30% weight
            min(avg_daily_sales / 10000, 1) * 40  # 40% weight, capped at 10,000 KES
        )

        # Determine grade
        if score >= 80:
            grade = 'A'
        elif score >= 70:
            grade = 'B'
        elif score >= 60:
            grade = 'C'
        elif score >= 50:
            grade = 'D'
        else:
            grade = 'E'

        # Save credit score
        credit_score, created = CreditScore.objects.update_or_create(
            business=business,
            defaults={
                'score': score,
                'score_grade': grade,
                'transaction_consistency': consistency,
                'average_balance': avg_daily_sales,
                'months_of_history': int(total_months),
                'calculation_version': '1.0'
            }
        )

        return credit_score