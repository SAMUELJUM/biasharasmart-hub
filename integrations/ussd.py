from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
import json
from accounts.models import User
from businesses.models import Business
from transactions.models import Transaction
from inventory.models import Product


class USSDHandler:
    """Handle USSD menu interactions"""

    @staticmethod
    @csrf_exempt
    def handle_request(request):
        """Main USSD request handler"""
        if request.method == 'POST':
            session_id = request.POST.get('sessionId')
            service_code = request.POST.get('serviceCode')
            phone_number = request.POST.get('phoneNumber')
            text = request.POST.get('text', '')

            # Parse USSD input
            user_input = text.split('*')

            # Get or create user session
            response = USSDHandler.process_menu(phone_number, user_input)

            return HttpResponse(response)

        return HttpResponse("END Invalid request")

    @staticmethod
    def process_menu(phone_number, user_input):
        """Process USSD menu based on input"""

        # Main menu
        if len(user_input) == 1 and user_input[0] == '':
            return USSDHandler.main_menu()

        # Check if user is registered
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return USSDHandler.registration_menu()

        # Handle menu navigation
        menu_level = len([i for i in user_input if i])

        if menu_level == 1:  # After main menu selection
            option = user_input[0]
            return USSDHandler.handle_main_menu_option(option, user)

        elif menu_level == 2:  # Sub-menu selection
            option = user_input[0]
            sub_option = user_input[1]
            return USSDHandler.handle_sub_menu(option, sub_option, user)

        elif menu_level >= 3:  # Data entry
            return USSDHandler.handle_data_entry(user_input, user)

        return USSDHandler.main_menu()

    @staticmethod
    def main_menu():
        """Display main menu"""
        response = "CON Welcome to BiasharaSmart Hub\n"
        response += "1. Check Balance\n"
        response += "2. Add Sale\n"
        response += "3. Add Expense\n"
        response += "4. Check Stock\n"
        response += "5. Add Stock\n"
        response += "6. Alerts\n"
        response += "7. Reports\n"
        response += "0. Exit"
        return response

    @staticmethod
    def registration_menu():
        """Display registration menu for new users"""
        response = "CON You are not registered.\n"
        response += "To register, send: REGISTER*YourName*BusinessName"
        return response

    @staticmethod
    def handle_main_menu_option(option, user):
        """Handle main menu selections"""
        businesses = Business.objects.filter(owner=user, is_active=True)

        if not businesses.exists():
            return "END No businesses found. Please register a business first."

        if option == '1':  # Check Balance
            return USSDHandler.check_balance_menu(businesses)

        elif option == '2':  # Add Sale
            return USSDHandler.add_transaction_menu(businesses, 'sale')

        elif option == '3':  # Add Expense
            return USSDHandler.add_transaction_menu(businesses, 'expense')

        elif option == '4':  # Check Stock
            return USSDHandler.check_stock_menu(businesses)

        elif option == '5':  # Add Stock
            return USSDHandler.add_stock_menu(businesses)

        elif option == '6':  # Alerts
            return USSDHandler.view_alerts(user)

        elif option == '7':  # Reports
            return USSDHandler.reports_menu(businesses)

        else:
            return "END Invalid option"

    @staticmethod
    def check_balance_menu(businesses):
        """Show business selection for balance check"""
        response = "CON Select business:\n"
        for i, business in enumerate(businesses[:5], 1):
            response += f"{i}. {business.name}\n"
        response += "0. Back"
        return response

    @staticmethod
    def add_transaction_menu(businesses, transaction_type):
        """Show transaction entry menu"""
        response = f"CON Add {transaction_type}\n"
        response += "Enter: BusinessNo*Amount*Description\n"
        for i, business in enumerate(businesses[:5], 1):
            response += f"{i}. {business.name}\n"
        return response

    @staticmethod
    def handle_data_entry(user_input, user):
        """Process data entry from USSD"""
        # Example: ['2', '1', '5000', 'Stock purchase']
        # Means: option 2 (Add Sale), business 1, amount 5000, description

        try:
            option = user_input[0]
            business_index = int(user_input[1])
            amount = float(user_input[2])
            description = user_input[3] if len(user_input) > 3 else ''

            # Get business
            businesses = list(Business.objects.filter(owner=user, is_active=True))
            if business_index <= len(businesses):
                business = businesses[business_index - 1]

                # Create transaction
                transaction_type = 'sale' if option == '2' else 'expense'
                Transaction.objects.create(
                    business=business,
                    transaction_type=transaction_type,
                    amount=amount,
                    description=description,
                    date=timezone.now().date(),
                    created_by=user
                )

                return f"END {transaction_type.title()} of KES {amount} recorded successfully!"
            else:
                return "END Invalid business selection"

        except (ValueError, IndexError):
            return "END Invalid input format"
        except Exception as e:
            return f"END Error: {str(e)}"