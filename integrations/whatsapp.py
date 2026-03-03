from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import json
import re
from datetime import datetime
from accounts.models import User
from businesses.models import Business
from transactions.models import Transaction
from analytics.models import Alert


class WhatsAppBot:
    """Handle WhatsApp business interactions"""

    @staticmethod
    @csrf_exempt
    def webhook(request):
        """Handle incoming WhatsApp messages"""
        if request.method == 'POST':
            data = json.loads(request.body)

            # Extract message details (format depends on WhatsApp Business API)
            phone_number = data.get('from')
            message = data.get('text', {}).get('body', '')

            # Process message
            response = WhatsAppBot.process_message(phone_number, message)

            # Send response back (you'd integrate with WhatsApp API here)
            WhatsAppBot.send_message(phone_number, response)

            return JsonResponse({'status': 'ok'})

        return HttpResponse("Webhook received")

    @staticmethod
    def process_message(phone_number, message):
        """Process natural language messages"""

        # Check if user exists
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return "Welcome to BiasharaSmart Hub! You're not registered yet. Please register via USSD (*123#) or web app to get started."

        # Convert message to lowercase for easier matching
        message = message.lower().strip()

        # Greeting
        if re.match(r'^(hi|hello|hey|habari|jambo)', message):
            return f"Hello {user.first_name}! How can I help you today?\n\nYou can ask me:\n- 'sales today'\n- 'expenses this week'\n- 'low stock'\n- 'alerts'\n- 'balance'"

        # Sales queries
        elif 'sales today' in message or 'sales t' in message:
            return WhatsAppBot.get_sales_today(user)

        elif 'sales yesterday' in message:
            return WhatsAppBot.get_sales_yesterday(user)

        elif 'sales this week' in message:
            return WhatsAppBot.get_sales_week(user)

        elif 'sales this month' in message:
            return WhatsAppBot.get_sales_month(user)

        # Expense queries
        elif 'expenses today' in message:
            return WhatsAppBot.get_expenses_today(user)

        elif 'expenses this week' in message:
            return WhatsAppBot.get_expenses_week(user)

        # Stock queries
        elif 'low stock' in message or 'stock alert' in message:
            return WhatsAppBot.get_low_stock(user)

        elif 'stock of' in message:
            product = message.replace('stock of', '').strip()
            return WhatsAppBot.get_product_stock(user, product)

        # Alerts
        elif 'alerts' in message or 'notifications' in message:
            return WhatsAppBot.get_alerts(user)

        # Balance/profit
        elif 'balance' in message or 'profit' in message:
            return WhatsAppBot.get_balance(user)

        # Help
        elif 'help' in message:
            return WhatsAppBot.get_help()

        # Unknown command
        else:
            return "I didn't understand that. Type 'help' to see what I can do."

    @staticmethod
    def get_sales_today(user):
        """Get today's sales"""
        today = datetime.now().date()
        businesses = Business.objects.filter(owner=user, is_active=True)

        total = 0
        for business in businesses:
            sales = Transaction.objects.filter(
                business=business,
                transaction_type='sale',
                date=today
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            total += sales

        return f"📊 *Sales Today*\nTotal: KES {total:,.2f}\n\nCheck the app for detailed breakdown."

    @staticmethod
    def get_low_stock(user):
        """Get low stock alerts"""
        from inventory.models import Product

        businesses = Business.objects.filter(owner=user, is_active=True)
        low_stock = Product.objects.filter(
            business__in=businesses,
            current_quantity__lte=models.F('reorder_level'),
            is_active=True
        )

        if not low_stock.exists():
            return "✅ All stock levels are healthy. No low stock items."

        response = "⚠️ *Low Stock Alerts*\n\n"
        for product in low_stock[:10]:
            response += f"• {product.name}: {product.current_quantity} {product.unit} (Reorder at {product.reorder_level})\n"

        if low_stock.count() > 10:
            response += f"\n...and {low_stock.count() - 10} more items"

        return response

    @staticmethod
    def get_alerts(user):
        """Get recent alerts"""
        businesses = Business.objects.filter(owner=user, is_active=True)
        alerts = Alert.objects.filter(
            business__in=businesses,
            is_read=False
        ).order_by('-created_at')[:5]

        if not alerts.exists():
            return "📬 No new alerts. Everything looks good!"

        response = "🔔 *Your Alerts*\n\n"
        for alert in alerts:
            response += f"• {alert.title}\n  {alert.message[:50]}...\n"

        return response

    @staticmethod
    def get_help():
        """Get help message"""
        return """
*BiasharaSmart Bot Help*

You can ask me:
• "sales today" - Today's sales
• "sales this week" - Weekly sales
• "expenses today" - Today's expenses
• "low stock" - Items below reorder level
• "stock of [product]" - Check specific product
• "alerts" - View notifications
• "balance" - Current profit/loss

For more features, use the web app or USSD (*123#)
        """