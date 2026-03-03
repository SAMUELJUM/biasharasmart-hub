from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
from django.shortcuts import get_object_or_404

from .models import Forecast, CreditScore, Alert
from .serializers import (
    ForecastSerializer, CreditScoreSerializer, AlertSerializer,
    DashboardSummarySerializer, AlertCreateSerializer, AlertBulkUpdateSerializer
)
from businesses.models import Business
from transactions.models import Transaction


# ============================================================================
# FORECAST VIEWS
# ============================================================================

class ForecastViewSet(viewsets.ModelViewSet):
    """ViewSet for Forecast operations"""
    serializer_class = ForecastSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter forecasts by user's businesses"""
        user = self.request.user
        return Forecast.objects.filter(
            business__owner=user
        ).select_related('business').order_by('-forecast_date', '-created_at')

    def perform_create(self, serializer):
        """Ensure business belongs to user"""
        business_id = self.request.data.get('business')
        business = get_object_or_404(Business, id=business_id, owner=self.request.user)
        serializer.save(business=business)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest forecasts for each business"""
        user = request.user
        businesses = Business.objects.filter(owner=user)

        latest_forecasts = []
        for business in businesses:
            forecast = Forecast.objects.filter(
                business=business
            ).order_by('-created_at').first()

            if forecast:
                latest_forecasts.append(forecast)

        serializer = self.get_serializer(latest_forecasts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def comparison(self, request, pk=None):
        """Compare forecast with actuals"""
        forecast = self.get_object()

        # Get actual transactions for the forecast period
        actuals = Transaction.objects.filter(
            business=forecast.business,
            transaction_type=forecast.forecast_type.rstrip('s'),  # 'sales' -> 'sale'
            date=forecast.forecast_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'forecast_id': forecast.id,
            'forecast_date': forecast.forecast_date,
            'predicted': forecast.predicted_value,
            'actual': actuals,
            'variance': actuals - forecast.predicted_value,
            'variance_percentage': ((
                                                actuals - forecast.predicted_value) / forecast.predicted_value * 100) if forecast.predicted_value else None
        })


# ============================================================================
# CREDIT SCORE VIEWS
# ============================================================================

class CreditScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Credit Score operations (read-only)"""
    serializer_class = CreditScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter credit scores by user's businesses"""
        user = self.request.user
        return CreditScore.objects.filter(
            business__owner=user
        ).select_related('business')

    @action(detail=False, methods=['get'])
    def my_business(self, request):
        """Get credit score for a specific business"""
        business_id = request.query_params.get('business_id')

        if not business_id:
            return Response(
                {'error': 'business_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify business ownership
        business = get_object_or_404(Business, id=business_id, owner=request.user)

        try:
            credit_score = CreditScore.objects.get(business=business)
            serializer = self.get_serializer(credit_score)
            return Response(serializer.data)
        except CreditScore.DoesNotExist:
            return Response(
                {'message': 'Credit score not yet calculated for this business'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def request_calculation(self, request):
        """Request credit score calculation"""
        business_id = request.data.get('business_id')

        if not business_id:
            return Response(
                {'error': 'business_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify business ownership
        business = get_object_or_404(Business, id=business_id, owner=request.user)

        # Trigger async calculation (you'll need to import the task)
        from .tasks import calculate_business_credit_score
        calculate_business_credit_score.delay(business_id)

        return Response({
            'message': 'Credit score calculation started',
            'business_id': business_id
        })


# ============================================================================
# ALERT VIEWS
# ============================================================================

class AlertViewSet(viewsets.ModelViewSet):
    """ViewSet for Alert operations"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return AlertCreateSerializer
        return AlertSerializer

    def get_queryset(self):
        """Filter alerts by user's businesses"""
        user = self.request.user
        queryset = Alert.objects.filter(
            business__owner=user
        ).select_related('business', 'related_product').order_by('-created_at')

        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # Filter by resolved status
        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')

        # Filter by alert type
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset

    def perform_create(self, serializer):
        """Ensure business belongs to user"""
        business_id = self.request.data.get('business')
        business = get_object_or_404(Business, id=business_id, owner=self.request.user)
        serializer.save(business=business)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update alerts (mark as read/resolved)"""
        serializer = AlertBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        alert_ids = serializer.validated_data['alert_ids']
        mark_as_read = serializer.validated_data.get('mark_as_read', False)
        mark_as_resolved = serializer.validated_data.get('mark_as_resolved', False)

        # Verify all alerts belong to user's businesses
        alerts = Alert.objects.filter(
            id__in=alert_ids,
            business__owner=request.user
        )

        if alerts.count() != len(alert_ids):
            return Response(
                {'error': 'Some alerts do not exist or do not belong to you'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update alerts
        update_data = {}
        if mark_as_read:
            update_data['is_read'] = True
        if mark_as_resolved:
            update_data['is_resolved'] = True
            update_data['resolved_at'] = timezone.now()

        if update_data:
            alerts.update(**update_data)

        return Response({
            'message': f'Updated {alerts.count()} alerts',
            'updated_ids': list(alerts.values_list('id', flat=True))
        })

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a single alert as read"""
        alert = self.get_object()
        alert.is_read = True
        alert.save()
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'])
    def mark_resolved(self, request, pk=None):
        """Mark a single alert as resolved"""
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'status': 'marked as resolved'})


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_dashboard(request):
    """
    Get analytics dashboard data for a business
    This is the view that was missing in your error
    """
    business_id = request.query_params.get('business_id')

    if not business_id:
        return Response(
            {'error': 'business_id parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify access
    try:
        business = Business.objects.get(id=business_id)
        if business.owner != request.user and not business.staff.filter(user=request.user, is_active=True).exists():
            return Response(
                {'error': 'You do not have access to this business'},
                status=status.HTTP_403_FORBIDDEN
            )
    except Business.DoesNotExist:
        return Response(
            {'error': 'Business not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get date range (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)

    # Sales data
    sales = Transaction.objects.filter(
        business=business,
        transaction_type='sale',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total=Sum('amount'),
        count=Count('id'),
        avg=Avg('amount')
    )

    # Expense data
    expenses = Transaction.objects.filter(
        business=business,
        transaction_type='expense',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )

    # Get latest forecast
    latest_forecast = Forecast.objects.filter(
        business=business,
        forecast_type='sales'
    ).order_by('-created_at').first()

    # Get credit score
    try:
        credit_score = CreditScore.objects.get(business=business)
        credit_score_data = CreditScoreSerializer(credit_score).data
    except CreditScore.DoesNotExist:
        credit_score_data = None

    # Get recent alerts
    recent_alerts = Alert.objects.filter(
        business=business,
        is_read=False
    ).order_by('-created_at')[:5]

    # Prepare response data
    data = {
        'period_start': start_date,
        'period_end': end_date,
        'sales': {
            'total': float(sales['total'] or 0),
            'count': sales['count'] or 0,
            'average': float(sales['avg'] or 0)
        },
        'expenses': {
            'total': float(expenses['total'] or 0),
            'count': expenses['count'] or 0
        },
        'profit': float((sales['total'] or 0) - (expenses['total'] or 0)),
        'forecast': {
            'predicted': float(latest_forecast.predicted_value) if latest_forecast else None,
            'date': latest_forecast.forecast_date if latest_forecast else None,
            'type': latest_forecast.forecast_type if latest_forecast else None
        } if latest_forecast else None,
        'credit_score': credit_score_data,
        'alerts': AlertSerializer(recent_alerts, many=True).data
    }

    serializer = DashboardSummarySerializer(data=data)
    serializer.is_valid()

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def business_health(request):
    """
    Get business health metrics
    """
    business_id = request.query_params.get('business_id')

    if not business_id:
        return Response(
            {'error': 'business_id parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify access (similar to above)
    try:
        business = Business.objects.get(id=business_id, owner=request.user)
    except Business.DoesNotExist:
        return Response(
            {'error': 'Business not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Calculate health metrics (simplified example)
    # In production, you'd have more sophisticated calculations

    # Get last 90 days of data
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=90)

    transactions = Transaction.objects.filter(
        business=business,
        date__gte=start_date,
        date__lte=end_date
    )

    # Calculate metrics
    total_sales = transactions.filter(transaction_type='sale').aggregate(s=Sum('amount'))['s'] or 0
    total_expenses = transactions.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or 0

    # Sample health calculation
    profitability = min(100, max(0, (total_sales - total_expenses) / (total_sales or 1) * 100))

    # Get transaction consistency
    days_with_transactions = transactions.dates('date', 'day').count()
    consistency = (days_with_transactions / 90) * 100

    # Overall health score (simplified)
    health_score = int((profitability * 0.5 + consistency * 0.5))

    if health_score >= 80:
        overall = 'Excellent'
    elif health_score >= 60:
        overall = 'Good'
    elif health_score >= 40:
        overall = 'Fair'
    elif health_score >= 20:
        overall = 'Poor'
    else:
        overall = 'Critical'

    return Response({
        'business_id': business.id,
        'business_name': business.name,
        'overall_health': overall,
        'health_score': health_score,
        'profitability_score': int(profitability),
        'liquidity_score': 70,  # Placeholder - implement actual calculation
        'efficiency_score': 65,  # Placeholder
        'growth_score': 75,  # Placeholder
        'stability_score': int(consistency),
        'recommendations': [
            'Maintain daily transaction records',
            'Consider reducing expenses',
            'Build emergency cash reserve'
        ] if health_score < 70 else [
            'Consider expansion opportunities',
            'Explore loan options for growth'
        ],
        'risk_factors': [
            {'factor': 'Cash flow volatility', 'level': 'Medium'},
            {'factor': 'Market dependency', 'level': 'Low'}
        ] if health_score < 50 else []
    })


# ============================================================================
# ANALYTICS REPORTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report(request):
    """
    Generate analytics report
    """
    report_type = request.data.get('report_type')
    business_id = request.data.get('business_id')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')

    if not all([report_type, business_id, start_date, end_date]):
        return Response(
            {'error': 'report_type, business_id, start_date, end_date are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verify access
    try:
        business = Business.objects.get(id=business_id, owner=request.user)
    except Business.DoesNotExist:
        return Response(
            {'error': 'Business not found or access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Parse dates
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate report based on type
    if report_type == 'summary':
        # Get summary data
        sales = Transaction.objects.filter(
            business=business,
            transaction_type='sale',
            date__gte=start,
            date__lte=end
        ).aggregate(total=Sum('amount'))['total'] or 0

        expenses = Transaction.objects.filter(
            business=business,
            transaction_type='expense',
            date__gte=start,
            date__lte=end
        ).aggregate(total=Sum('amount'))['total'] or 0

        data = {
            'total_sales': sales,
            'total_expenses': expenses,
            'net_profit': sales - expenses,
            'transaction_count': Transaction.objects.filter(
                business=business,
                date__gte=start,
                date__lte=end
            ).count()
        }

    elif report_type == 'detailed':
        # Get detailed transaction data
        transactions = Transaction.objects.filter(
            business=business,
            date__gte=start,
            date__lte=end
        ).order_by('-date')

        from transactions.serializers import TransactionSerializer
        data = TransactionSerializer(transactions, many=True).data

    elif report_type == 'forecast':
        # Get forecast data
        forecasts = Forecast.objects.filter(
            business=business,
            forecast_date__gte=start,
            forecast_date__lte=end
        ).order_by('forecast_date')

        data = ForecastSerializer(forecasts, many=True).data

    else:
        return Response(
            {'error': 'Invalid report type'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'business_id': business.id,
        'business_name': business.name,
        'report_type': report_type,
        'start_date': start,
        'end_date': end,
        'generated_at': timezone.now(),
        'data': data
    })