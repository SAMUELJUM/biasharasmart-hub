from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings  # ← FIX 1: was missing
import os


def home(request):
    return render(request, 'home/index.html')


def api_root(request):
    return JsonResponse({
        'name': 'BiasharaSmart Hub API',
        'version': '1.0',
        'description': 'AI-Powered Business Intelligence Platform for Kenyan SMEs',
        'endpoints': {
            'admin': '/admin/',
            'authentication': {
                'register': '/api/auth/register/',
                'login': '/api/auth/login/',
                'verify_otp': '/api/auth/verify-otp/',
                'refresh': '/api/auth/refresh/',
                'profile': '/api/auth/profile/',
            },
            'businesses': '/api/businesses/',
            'transactions': '/api/transactions/',
            'inventory': '/api/inventory/',
            'analytics': {
                'dashboard': '/api/analytics/dashboard/',
                'forecasts': '/api/analytics/forecasts/',
                'credit_scores': '/api/analytics/credit-scores/',
                'alerts': '/api/analytics/alerts/',
                'business_health': '/api/analytics/business-health/',
                'generate_report': '/api/analytics/generate-report/',
            },
            'reports': '/api/reports/',
        },
        'documentation': 'See README.md for detailed API documentation',
        'status': 'active',
        'timestamp': timezone.now().isoformat(),
    })


def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'database': 'connected',
        'services': {
            'authentication': 'operational',
            'api': 'operational',
        }
    })


@login_required(login_url='/login/')
def help_page(request):
    toc_items = [
        {'id': 1,  'num': '01', 'title': 'Getting Started — Registration'},
        {'id': 2,  'num': '02', 'title': 'Verifying Your Phone (OTP)'},
        {'id': 3,  'num': '03', 'title': 'Logging In'},
        {'id': 4,  'num': '04', 'title': 'Setting Up Your Business'},
        {'id': 5,  'num': '05', 'title': 'Understanding Your Dashboard'},
        {'id': 6,  'num': '06', 'title': 'Recording Sales'},
        {'id': 7,  'num': '07', 'title': 'Recording Expenses'},
        {'id': 8,  'num': '08', 'title': 'Managing Inventory'},
        {'id': 9,  'num': '09', 'title': 'Viewing Transactions'},
        {'id': 10, 'num': '10', 'title': 'Analytics & Reports'},
        {'id': 11, 'num': '11', 'title': 'Managing Customers'},
        {'id': 12, 'num': '12', 'title': 'Managing Suppliers'},
        {'id': 13, 'num': '13', 'title': 'Understanding Alerts'},
        {'id': 14, 'num': '14', 'title': 'Account Settings'},
        {'id': 15, 'num': '15', 'title': 'USSD Access (*123#)'},
        {'id': 16, 'num': '16', 'title': 'WhatsApp Bot'},
        {'id': 17, 'num': '17', 'title': 'Subscription Plans'},
        {'id': 18, 'num': '18', 'title': 'Troubleshooting & FAQs'},
    ]
    faqs = [
        {'q': 'I did not receive my OTP', 'a': 'Check your number is in 254XXXXXXXXX format. Ensure you have signal. Click Resend OTP. Codes expire after 5 minutes.'},
        {'q': 'I cannot log in', 'a': 'Your login username is your phone number (254XXXXXXXXX). Use Forgot Password if needed.'},
        {'q': 'Dashboard shows no data', 'a': 'Add a business profile first, then record some transactions. New accounts start empty.'},
        {'q': 'My sale did not save', 'a': 'Check all required fields are filled (business, amount, payment mode, date). Ensure you have stable internet.'},
        {'q': 'Stock is not decreasing after a POS sale', 'a': 'Products must be added to Inventory for stock to auto-deduct. Make sure the product exists in your inventory list.'},
        {'q': 'I cannot see my businesses in dropdowns', 'a': 'Go to the Business section and add your business profile first, then refresh the page.'},
        {'q': 'My report is empty', 'a': 'Ensure there are transactions in the selected date range. Try widening the date range.'},
        {'q': 'WhatsApp bot is not responding', 'a': 'Send "Hi" again to restart the session. Ensure you are messaging the correct number.'},
        {'q': 'I was logged out automatically', 'a': 'For security, the system logs out inactive sessions. Simply log in again — this is normal.'},
    ]
    return render(request, 'home/help.html', {
        'user': request.user,
        'toc_items': toc_items,
        'faqs': faqs,
        'total_sections': 18,
    })


@login_required(login_url='/login/')
def download_user_guide(request):
    # FIX 2: proper fallback + existence check
    static_base = settings.STATIC_ROOT or os.path.join(settings.BASE_DIR, 'static')
    file_path = os.path.join(static_base, 'docs', 'BiasharaSmart_User_Guide.docx')

    if not os.path.exists(file_path):
        file_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'BiasharaSmart_User_Guide.docx')

    if not os.path.exists(file_path):
        raise Http404("User guide file not found.")

    response = FileResponse(
        open(file_path, 'rb'),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = 'attachment; filename="BiasharaSmart_User_Guide.docx"'
    return response


@login_required(login_url='/login/')
def onboarding(request):
    if request.method == 'POST':
        request.user.has_seen_onboarding = True
        request.user.save(update_fields=['has_seen_onboarding'])
        next_url = request.POST.get('next', '/dashboard/')
        # Safety check — only allow relative URLs
        if not next_url.startswith('/'):
            next_url = '/dashboard/'
        return redirect(next_url)
    return render(request, 'home/onboarding.html', {'user': request.user})