from rest_framework import serializers
from django.utils import timezone
from .models import Forecast, CreditScore, Alert
from businesses.models import Business


# ============================================================================
# FORECAST SERIALIZERS
# ============================================================================

class ForecastSerializer(serializers.ModelSerializer):
    """Serializer for AI-generated forecasts"""

    # Read-only fields for related data
    business_name = serializers.CharField(source='business.name', read_only=True)

    # Formatted fields for display
    formatted_predicted_value = serializers.SerializerMethodField()
    formatted_forecast_date = serializers.SerializerMethodField()
    forecast_type_display = serializers.CharField(source='get_forecast_type_display', read_only=True)

    class Meta:
        model = Forecast
        fields = [
            'id',
            'business',
            'business_name',
            'forecast_type',
            'forecast_type_display',
            'forecast_date',
            'formatted_forecast_date',
            'predicted_value',
            'formatted_predicted_value',
            'lower_bound',
            'upper_bound',
            'confidence_level',
            'model_used',
            'training_data_points',
            'accuracy_metric',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'business_name',
            'created_at',
            'model_used',
            'training_data_points',
            'accuracy_metric'
        ]

    def get_formatted_predicted_value(self, obj):
        """Format predicted value as KES currency"""
        if obj.predicted_value:
            return f"KES {obj.predicted_value:,.2f}"
        return None

    def get_formatted_forecast_date(self, obj):
        """Format forecast date"""
        if obj.forecast_date:
            return obj.forecast_date.strftime('%d %b %Y')
        return None

    def validate(self, data):
        """Validate forecast data"""
        # Ensure forecast_date is not in the past (for new forecasts)
        if not self.instance and data.get('forecast_date', timezone.now().date()) < timezone.now().date():
            raise serializers.ValidationError({
                'forecast_date': 'Forecast date cannot be in the past'
            })

        # Validate bounds if provided
        if data.get('lower_bound') and data.get('upper_bound'):
            if data['lower_bound'] > data['upper_bound']:
                raise serializers.ValidationError({
                    'bounds': 'Lower bound cannot be greater than upper bound'
                })

        return data


class ForecastListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing forecasts"""

    forecast_type_display = serializers.CharField(source='get_forecast_type_display', read_only=True)
    short_description = serializers.SerializerMethodField()

    class Meta:
        model = Forecast
        fields = [
            'id',
            'forecast_type',
            'forecast_type_display',
            'forecast_date',
            'predicted_value',
            'short_description',
            'created_at'
        ]

    def get_short_description(self, obj):
        """Generate short description for list view"""
        return f"{obj.get_forecast_type_display()} for {obj.forecast_date}: KES {obj.predicted_value:,.2f}"


class ForecastComparisonSerializer(serializers.Serializer):
    """Serializer for comparing forecasts with actuals"""

    forecast_date = serializers.DateField()
    predicted = serializers.DecimalField(max_digits=15, decimal_places=2)
    actual = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance_percentage = serializers.FloatField(read_only=True)

    def to_representation(self, instance):
        """Calculate variance when returning data"""
        data = super().to_representation(instance)

        if data['actual'] is not None:
            data['variance'] = data['actual'] - data['predicted']
            if data['predicted'] != 0:
                data['variance_percentage'] = (data['variance'] / data['predicted']) * 100
            else:
                data['variance_percentage'] = None

        return data


# ============================================================================
# CREDIT SCORE SERIALIZERS
# ============================================================================

class CreditScoreSerializer(serializers.ModelSerializer):
    """Serializer for credit scores"""

    # Read-only fields
    business_name = serializers.CharField(source='business.name', read_only=True)
    score_grade_display = serializers.CharField(source='get_score_grade_display', read_only=True)

    # Formatted fields
    formatted_score = serializers.SerializerMethodField()
    formatted_last_calculated = serializers.SerializerMethodField()
    credit_rating = serializers.SerializerMethodField()
    loan_recommendation = serializers.SerializerMethodField()

    class Meta:
        model = CreditScore
        fields = [
            'id',
            'business',
            'business_name',
            'score',
            'formatted_score',
            'score_grade',
            'score_grade_display',
            'credit_rating',
            'transaction_consistency',
            'average_balance',
            'months_of_history',
            'repayment_history_score',
            'last_calculated',
            'formatted_last_calculated',
            'calculation_version',
            'loan_recommendation'
        ]
        read_only_fields = [
            'id',
            'business_name',
            'last_calculated',
            'calculation_version'
        ]

    def get_formatted_score(self, obj):
        """Format score with grade"""
        return f"{obj.score} ({obj.score_grade})"

    def get_formatted_last_calculated(self, obj):
        """Format last calculated date"""
        if obj.last_calculated:
            return obj.last_calculated.strftime('%d %b %Y %H:%M')
        return None

    def get_credit_rating(self, obj):
        """Provide detailed credit rating description"""
        ratings = {
            'A': 'Excellent - Low risk, eligible for premium loan products',
            'B': 'Good - Moderate risk, eligible for standard loans',
            'C': 'Fair - Acceptable risk,可能需要 collateral',
            'D': 'Poor - High risk, limited loan options',
            'E': 'Very Poor - Very high risk, consider alternative financing'
        }
        return ratings.get(obj.score_grade, 'Unknown rating')

    def get_loan_recommendation(self, obj):
        """Generate loan recommendation based on score"""
        if obj.score >= 80:
            return {
                'eligible': True,
                'max_amount': obj.average_balance * 3,
                'interest_rate': '12-15%',
                'products': ['Business Loan', 'Asset Financing', 'Overdraft']
            }
        elif obj.score >= 70:
            return {
                'eligible': True,
                'max_amount': obj.average_balance * 2,
                'interest_rate': '15-18%',
                'products': ['Business Loan', 'Invoice Discounting']
            }
        elif obj.score >= 60:
            return {
                'eligible': True,
                'max_amount': obj.average_balance * 1.5,
                'interest_rate': '18-22%',
                'products': ['Micro Loan', 'Group Loan'],
                'requirements': ['可能需要 guarantor']
            }
        elif obj.score >= 50:
            return {
                'eligible': 'Conditional',
                'max_amount': obj.average_balance,
                'interest_rate': '22-25%',
                'products': ['Secured Loan'],
                'requirements': ['Collateral required', 'Group guarantee']
            }
        else:
            return {
                'eligible': False,
                'message': 'Build transaction history to improve credit score',
                'recommendations': [
                    'Record all sales daily',
                    'Maintain consistent cash flow',
                    'Reduce cash flow volatility',
                    'Build at least 6 months of transaction history'
                ]
            }


class CreditScoreHistorySerializer(serializers.ModelSerializer):
    """Serializer for credit score history (if you add history tracking)"""

    class Meta:
        model = CreditScore
        fields = ['score', 'score_grade', 'last_calculated']


# ============================================================================
# ALERT SERIALIZERS
# ============================================================================

class AlertSerializer(serializers.ModelSerializer):
    """Serializer for system-generated alerts"""

    # Read-only fields
    business_name = serializers.CharField(source='business.name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    # Related product info
    product_name = serializers.CharField(source='related_product.name', read_only=True, allow_null=True)
    product_sku = serializers.CharField(source='related_product.sku', read_only=True, allow_null=True)

    # Formatted fields
    time_ago = serializers.SerializerMethodField()
    formatted_created_at = serializers.SerializerMethodField()

    # Action URLs
    action_url = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id',
            'business',
            'business_name',
            'alert_type',
            'alert_type_display',
            'severity',
            'severity_display',
            'title',
            'message',
            'related_product',
            'product_name',
            'product_sku',
            'suggested_action',
            'action_data',
            'action_url',
            'is_read',
            'is_resolved',
            'resolved_at',
            'created_at',
            'formatted_created_at',
            'time_ago'
        ]
        read_only_fields = [
            'id',
            'business_name',
            'created_at',
            'resolved_at'
        ]

    def get_time_ago(self, obj):
        """Calculate time ago string"""
        from django.utils.timesince import timesince
        from django.utils import timezone

        if obj.created_at:
            return f"{timesince(obj.created_at, timezone.now())} ago"
        return None

    def get_formatted_created_at(self, obj):
        """Format created at date"""
        if obj.created_at:
            return obj.created_at.strftime('%d %b %Y %H:%M')
        return None

    def get_action_url(self, obj):
        """Generate action URL based on alert type"""
        if obj.alert_type == 'low_stock' and obj.related_product:
            return f"/inventory/products/{obj.related_product.id}/reorder/"
        elif obj.alert_type == 'reorder_suggestion' and obj.related_product:
            return f"/inventory/products/{obj.related_product.id}/reorder/"
        elif obj.alert_type == 'payment_due':
            return "/transactions/add/?type=expense"
        return None

    def validate(self, data):
        """Validate alert data"""
        # Ensure severity matches alert type patterns
        alert_type = data.get('alert_type')
        severity = data.get('severity')

        critical_types = ['cashflow_warning']
        warning_types = ['low_stock', 'payment_due']

        if alert_type in critical_types and severity != 'critical':
            raise serializers.ValidationError({
                'severity': f'{alert_type} alerts should be critical severity'
            })

        if alert_type in warning_types and severity not in ['warning', 'critical']:
            raise serializers.ValidationError({
                'severity': f'{alert_type} alerts should be warning or critical'
            })

        return data


class AlertCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating alerts"""

    class Meta:
        model = Alert
        fields = [
            'business',
            'alert_type',
            'severity',
            'title',
            'message',
            'related_product',
            'suggested_action',
            'action_data'
        ]

    def validate(self, data):
        """Validate alert creation"""
        # Ensure title and message are provided
        if not data.get('title'):
            raise serializers.ValidationError({'title': 'Title is required'})

        if not data.get('message'):
            raise serializers.ValidationError({'message': 'Message is required'})

        # Validate action data structure if provided
        action_data = data.get('action_data')
        if action_data and not isinstance(action_data, dict):
            raise serializers.ValidationError({
                'action_data': 'Action data must be a JSON object'
            })

        return data


class AlertBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating alerts"""

    alert_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    mark_as_read = serializers.BooleanField(required=False, default=False)
    mark_as_resolved = serializers.BooleanField(required=False, default=False)

    def validate_alert_ids(self, value):
        """Validate that all alert IDs exist"""
        from .models import Alert

        existing_ids = set(Alert.objects.filter(id__in=value).values_list('id', flat=True))
        missing_ids = set(value) - existing_ids

        if missing_ids:
            raise serializers.ValidationError(
                f"Alerts with IDs {missing_ids} do not exist"
            )

        return value


# ============================================================================
# DASHBOARD AND ANALYTICS SERIALIZERS
# ============================================================================

class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary data"""

    period_start = serializers.DateField()
    period_end = serializers.DateField()

    # Sales data
    sales = serializers.DictField()
    expenses = serializers.DictField()
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)

    # Forecast data
    forecast = serializers.DictField(allow_null=True)

    # Credit score
    credit_score = serializers.DictField(allow_null=True)

    # Alerts
    alerts = AlertSerializer(many=True)

    # Inventory stats (optional)
    inventory_stats = serializers.DictField(required=False, allow_null=True)


class TimeSeriesDataPointSerializer(serializers.Serializer):
    """Serializer for time series data points"""

    date = serializers.DateField()
    value = serializers.DecimalField(max_digits=15, decimal_places=2)
    label = serializers.CharField(required=False, allow_blank=True)


class AnalyticsReportSerializer(serializers.Serializer):
    """Serializer for comprehensive analytics report"""

    business_id = serializers.IntegerField()
    report_type = serializers.ChoiceField(choices=['summary', 'detailed', 'forecast', 'credit'])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    generated_at = serializers.DateTimeField(read_only=True)

    # Dynamic fields based on report type
    data = serializers.DictField()


# ============================================================================
# BUSINESS INTELLIGENCE SERIALIZERS
# ============================================================================

class BusinessHealthSerializer(serializers.Serializer):
    """Serializer for business health metrics"""

    overall_health = serializers.ChoiceField(choices=['Excellent', 'Good', 'Fair', 'Poor', 'Critical'])
    health_score = serializers.IntegerField(min_value=0, max_value=100)

    # Component scores
    profitability_score = serializers.IntegerField(min_value=0, max_value=100)
    liquidity_score = serializers.IntegerField(min_value=0, max_value=100)
    efficiency_score = serializers.IntegerField(min_value=0, max_value=100)
    growth_score = serializers.IntegerField(min_value=0, max_value=100)
    stability_score = serializers.IntegerField(min_value=0, max_value=100)

    # Recommendations
    recommendations = serializers.ListField(child=serializers.CharField())

    # Risk factors
    risk_factors = serializers.ListField(child=serializers.DictField())


class PerformanceInsightSerializer(serializers.Serializer):
    """Serializer for performance insights"""

    insight_type = serializers.ChoiceField(choices=[
        'trend', 'anomaly', 'opportunity', 'warning', 'achievement'
    ])
    title = serializers.CharField()
    description = serializers.CharField()
    impact = serializers.CharField(allow_blank=True)
    metric_name = serializers.CharField()
    metric_value = serializers.FloatField()
    benchmark_value = serializers.FloatField(allow_null=True)
    recommendation = serializers.CharField(allow_blank=True)


# ============================================================================
# HELPER FUNCTIONS AND VALIDATORS
# ============================================================================

def validate_date_range(data):
    """Validate that start_date is before end_date"""
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if start_date and end_date and start_date > end_date:
        raise serializers.ValidationError({
            'date_range': 'Start date must be before end date'
        })

    return data


def validate_forecast_horizon(days):
    """Validate forecast horizon is within limits"""
    if days < 1:
        raise serializers.ValidationError("Forecast horizon must be at least 1 day")
    if days > 365:
        raise serializers.ValidationError("Forecast horizon cannot exceed 365 days")
    return days