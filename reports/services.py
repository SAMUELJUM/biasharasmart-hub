import csv
import io
import pdfkit
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.template.loader import get_template
from django.db.models import Sum, Count, Q
from transactions.models import Transaction
from inventory.models import Product
from analytics.models import Forecast


class ReportGenerator:
    """Generate various business reports"""

    @staticmethod
    def generate_sales_report(business_id, start_date, end_date, format='csv'):
        """Generate sales report for date range"""

        transactions = Transaction.objects.filter(
            business_id=business_id,
            transaction_type='sale',
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        if format == 'csv':
            return ReportGenerator._sales_report_csv(transactions, start_date, end_date)
        elif format == 'pdf':
            return ReportGenerator._sales_report_pdf(transactions, start_date, end_date, business_id)
        else:  # HTML
            return ReportGenerator._sales_report_html(transactions, start_date, end_date, business_id)

    @staticmethod
    def _sales_report_csv(transactions, start_date, end_date):
        """Generate CSV sales report"""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(['Date', 'Amount', 'Category', 'Payment Mode', 'Description'])

        # Write data
        total = 0
        for t in transactions:
            writer.writerow([
                t.date,
                t.amount,
                t.category.name if t.category else 'N/A',
                t.payment_mode,
                t.description
            ])
            total += t.amount

        # Write summary
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Period', f"{start_date} to {end_date}"])
        writer.writerow(['Total Transactions', transactions.count()])
        writer.writerow(['Total Sales', f"KES {total:,.2f}"])

        # Prepare response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_{end_date}.csv"'

        return response

    @staticmethod
    def _sales_report_html(transactions, start_date, end_date, business_id):
        """Generate HTML sales report"""
        from businesses.models import Business

        business = Business.objects.get(id=business_id)

        # Calculate totals
        total_sales = transactions.aggregate(total=Sum('amount'))['total'] or 0
        avg_sale = transactions.aggregate(avg=Sum('amount') / Count('id'))['avg'] or 0

        # Group by category
        by_category = transactions.values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        # Group by payment mode
        by_payment = transactions.values('payment_mode').annotate(
            total=Sum('amount')
        ).order_by('-total')

        context = {
            'business': business,
            'start_date': start_date,
            'end_date': end_date,
            'transactions': transactions,
            'total_sales': total_sales,
            'avg_sale': avg_sale,
            'transaction_count': transactions.count(),
            'by_category': by_category,
            'by_payment': by_payment,
            'generated_at': datetime.now()
        }

        template = get_template('reports/sales_report.html')
        html = template.render(context)

        return HttpResponse(html)

    @staticmethod
    def generate_profit_loss(business_id, start_date, end_date):
        """Generate profit and loss statement"""

        # Get all transactions
        sales = Transaction.objects.filter(
            business_id=business_id,
            transaction_type='sale',
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        expenses = Transaction.objects.filter(
            business_id=business_id,
            transaction_type='expense',
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Get cost of goods sold (simplified - from purchases)
        purchases = Transaction.objects.filter(
            business_id=business_id,
            transaction_type='purchase',
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        gross_profit = sales - purchases
        net_profit = gross_profit - expenses

        context = {
            'start_date': start_date,
            'end_date': end_date,
            'sales': sales,
            'purchases': purchases,
            'expenses': expenses,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'gross_margin': (gross_profit / sales * 100) if sales > 0 else 0,
            'net_margin': (net_profit / sales * 100) if sales > 0 else 0
        }

        template = get_template('reports/profit_loss.html')
        html = template.render(context)

        return HttpResponse(html)