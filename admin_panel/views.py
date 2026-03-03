from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
import json

from accounts.models import User
from businesses.models import Business
from transactions.models import Transaction
from inventory.models import Product
from analytics.models import Alert, CreditScore


# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_dashboard(request):
    """Admin dashboard with statistics"""

    # ===== PREVENT REDIRECT LOOPS =====
    # Check if there's a next parameter pointing to login
    next_url = request.GET.get('next', '')
    referer = request.META.get('HTTP_REFERER', '')

    # If next parameter points to login, remove it by redirecting to clean URL
    if next_url in ['/login/', '/login', '/accounts/login/', '/accounts/login']:
        print(f"⚠️ Detected potential redirect loop - removing next parameter: {next_url}")
        return redirect('/admin-panel/')

    # If referer is login page, this might be a redirect loop
    if referer and ('/login' in referer or '/accounts/login' in referer):
        print(f"⚠️ Request came from login page, checking for loop condition")
        # Check if this is a loop by looking at session
        loop_count = request.session.get('admin_access_attempts', 0)
        if loop_count > 2:
            print(f"❌ Detected redirect loop! Too many attempts: {loop_count}")
            # Clear the loop counter
            request.session['admin_access_attempts'] = 0
            return HttpResponse("""
                <html>
                <head><title>Redirect Loop Detected</title></head>
                <body>
                    <h1>Redirect Loop Detected</h1>
                    <p>We've detected a redirect loop. This might be caused by authentication issues.</p>
                    <p>Please try:</p>
                    <ul>
                        <li><a href="/login/?next=/admin-panel/">Login again</a></li>
                        <li><a href="/admin-panel/test/">Check admin test page</a></li>
                        <li><a href="/admin-panel/health/">Check health endpoint</a></li>
                    </ul>
                </body>
                </html>
            """)
        else:
            request.session['admin_access_attempts'] = loop_count + 1
            print(f"📊 Admin access attempt #{loop_count + 1}")
    else:
        # Reset loop counter if request came from elsewhere
        request.session['admin_access_attempts'] = 0
    # ===================================

    # ===== ENHANCED DEBUG INFORMATION =====
    print("\n" + "=" * 60)
    print("🚀 ADMIN DASHBOARD ACCESSED - DETAILED DEBUG INFO")
    print("=" * 60)
    print(f"📅 Timestamp: {timezone.now()}")
    print(f"👤 User: {request.user}")
    print(f"🆔 User ID: {request.user.id}")
    print(f"📱 Phone: {getattr(request.user, 'phone_number', 'N/A')}")
    print(f"🔑 Authenticated: {request.user.is_authenticated}")
    print(f"👑 Is Staff: {request.user.is_staff}")
    print(f"⭐ Is Superuser: {request.user.is_superuser}")
    print(f"✅ Is Active: {request.user.is_active}")
    print(f"📧 Email: {request.user.email}")
    print(f"📝 Session Key: {request.session.session_key}")
    print(f"💾 Session Data: {dict(request.session.items())}")
    print(f"🔍 Next parameter: {next_url}")
    print(f"🔗 Referer: {referer}")

    # Check cookies
    print(f"🍪 Cookies: {request.COOKIES}")

    # Check headers (sanitized)
    headers = {k: v for k, v in request.headers.items()
               if not k.lower() in ['authorization', 'cookie', 'csrf-token']}
    print(f"📋 Headers (sanitized): {headers}")

    # Check if Authorization header exists
    auth_header = request.headers.get('Authorization', 'Not present')
    if auth_header != 'Not present':
        # Show only first 20 chars for security
        print(f"🔐 Auth Header: {auth_header[:20]}...")
    else:
        print(f"🔐 Auth Header: {auth_header}")

    # Check for token in session
    print(f"🎫 Token in session: {'access_token' in request.session}")

    # Get user permissions
    print(f"🔓 User permissions: {list(request.user.get_all_permissions())}")

    # Check if user can access admin
    if request.user.is_staff:
        print("✅ User has staff privileges - admin access granted")
    else:
        print("❌ User does NOT have staff privileges - admin access should be denied")

    # Check user groups
    groups = request.user.groups.all()
    print(f"👥 User groups: {[group.name for group in groups]}")

    # Check if user is in any admin group
    admin_groups = groups.filter(name__icontains='admin')
    if admin_groups.exists():
        print(f"✅ User is in admin groups: {[g.name for g in admin_groups]}")

    # Check URL that was requested
    print(f"🌐 Requested URL: {request.build_absolute_uri()}")
    print(f"📍 Path: {request.path}")
    print(f"🔄 Referer: {request.META.get('HTTP_REFERER', 'None')}")

    print("=" * 60 + "\n")
    # ======================================

    # Get statistics with error handling
    try:
        context = {
            'total_users': User.objects.count(),
            'total_businesses': Business.objects.count(),
            'total_transactions': Transaction.objects.count(),
            'total_products': Product.objects.count(),
            'pending_alerts': Alert.objects.filter(is_resolved=False).count(),

            'recent_users': User.objects.order_by('-date_joined')[:10],
            'recent_businesses': Business.objects.order_by('-created_at')[:10],
            'recent_transactions': Transaction.objects.order_by('-created_at')[:10],
            'recent_alerts': Alert.objects.filter(is_resolved=False).order_by('-created_at')[:10],

            'today_sales': Transaction.objects.filter(
                transaction_type='sale',
                date=timezone.now().date()
            ).aggregate(total=Sum('amount'))['total'] or 0,

            'monthly_sales': Transaction.objects.filter(
                transaction_type='sale',
                date__gte=timezone.now().date() - timedelta(days=30)
            ).aggregate(total=Sum('amount'))['total'] or 0,

            # Additional stats for debugging
            'debug_info': {
                'user_id': request.user.id,
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser,
                'session_key': request.session.session_key,
            }
        }

        # Log successful context creation
        print(f"✅ Context created successfully with {context['total_users']} users")

    except Exception as e:
        print(f"❌ Error creating context: {str(e)}")
        context = {'error': str(e)}

    return render(request, 'admin_panel/dashboard.html', context)


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_users(request):
    from django.db.models import Count

    users = User.objects.all().annotate(
        businesses_count=Count('businesses', distinct=True)  # ← 'businesses' not 'business'
    ).order_by('-date_joined')

    now = timezone.now()
    this_month = users.filter(
        date_joined__year=now.year,
        date_joined__month=now.month
    ).count()

    return render(request, 'admin_panel/users.html', {
        'user': request.user,
        'all_users': users,
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
        'admin_users': users.filter(is_staff=True).count(),
        'new_this_month': this_month,
    })


@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_subscriptions(request):
    from django.db.models import Count

    users = User.objects.all().annotate(
        businesses_count=Count('businesses', distinct=True)
    ).order_by('-date_joined')

    subscriptions = []
    for u in users:
        subscriptions.append({
            'id':               u.id,
            'user_name':        u.get_full_name() or u.username,
            'user_phone':       u.phone_number or '',
            'plan':             u.subscription_plan,
            'status':           u.subscription_status,
            'start_date':       u.date_joined.date().isoformat() if u.date_joined else '',
            'end_date':         u.subscription_end.isoformat() if u.subscription_end else '',
            'businesses_count': u.businesses_count,
            'amount_paid':      0,
        })

    import json
    free_count       = sum(1 for s in subscriptions if s['plan'] == 'free')
    pro_count        = sum(1 for s in subscriptions if s['plan'] == 'pro')
    enterprise_count = sum(1 for s in subscriptions if s['plan'] == 'enterprise')
    active_count     = sum(1 for s in subscriptions if s['status'] == 'active')

    return render(request, 'admin_panel/subscriptions.html', {
        'user':             request.user,
        'subscriptions':    json.dumps(subscriptions),
        'total_subs':       len(subscriptions),
        'free_count':       free_count,
        'pro_count':        pro_count,
        'enterprise_count': enterprise_count,
        'active_count':     active_count,
    })


@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_logs(request):
    from accounts.models import SystemLog
    from django.utils import timezone

    today = timezone.now().date()
    today_logs = SystemLog.objects.filter(timestamp__date=today)

    return render(request, 'admin_panel/logs.html', {
        'user':         request.user,
        'total_today':  today_logs.count(),
        'errors_today': today_logs.filter(level='error').count(),
        'warn_today':   today_logs.filter(level='warning').count(),
        'info_today':   today_logs.filter(level='info').count(),
    })

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_user_detail(request, user_id):
    """User details - view specific user"""
    print(f"\n👤 ADMIN USER DETAIL accessed by: {request.user.phone_number} for user_id: {user_id}")
    user = get_object_or_404(User, id=user_id)
    businesses = Business.objects.filter(owner=user)
    transactions = Transaction.objects.filter(business__in=businesses).order_by('-created_at')[:20]

    context = {
        'user': user,
        'businesses': businesses,
        'transactions': transactions,
    }
    print(f"   Found {businesses.count()} businesses and {transactions.count()} transactions")
    return render(request, 'admin_panel/user_detail.html', context)


# ============================================================================
# BUSINESS MANAGEMENT
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_businesses(request):
    """Business management - list all businesses"""
    print(f"\n🏢 ADMIN BUSINESSES accessed by: {request.user.phone_number}")
    businesses = Business.objects.all().select_related('owner').order_by('-created_at')
    print(f"   Found {businesses.count()} businesses")

    return render(request, 'admin_panel/businesses.html', {'businesses': businesses})


@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_business_detail(request, business_id):
    """Business details - view specific business"""
    print(f"\n🏢 ADMIN BUSINESS DETAIL accessed by: {request.user.phone_number} for business_id: {business_id}")
    business = get_object_or_404(Business, id=business_id)
    products = Product.objects.filter(business=business)
    transactions = Transaction.objects.filter(business=business).order_by('-created_at')[:20]
    alerts = Alert.objects.filter(business=business, is_resolved=False)

    try:
        credit_score = CreditScore.objects.get(business=business)
    except CreditScore.DoesNotExist:
        credit_score = None

    context = {
        'business': business,
        'products': products,
        'transactions': transactions,
        'alerts': alerts,
        'credit_score': credit_score,
    }

    print(f"   Business: {business.name}, Products: {products.count()}, Transactions: {transactions.count()}")
    return render(request, 'admin_panel/business_detail.html', context)


# ============================================================================
# TRANSACTION MANAGEMENT
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_transactions(request):
    """Transaction management - list all transactions"""
    print(f"\n💰 ADMIN TRANSACTIONS accessed by: {request.user.phone_number}")
    transactions = Transaction.objects.all().select_related(
        'business', 'category', 'created_by'
    ).order_by('-created_at')

    print(f"   Found {transactions.count()} transactions")
    return render(request, 'admin_panel/transactions.html', {'transactions': transactions})


# ============================================================================
# ALERT MANAGEMENT
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_alerts(request):
    """Alert management - list all alerts"""
    print(f"\n⚠️ ADMIN ALERTS accessed by: {request.user.phone_number}")
    alerts = Alert.objects.all().select_related(
        'business', 'related_product'
    ).order_by('-created_at')

    print(f"   Found {alerts.count()} alerts")
    return render(request, 'admin_panel/alerts.html', {'alerts': alerts})


# ============================================================================
# ANALYTICS
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_analytics(request):
    """System analytics - platform statistics"""
    print(f"\n📊 ADMIN ANALYTICS accessed by: {request.user.phone_number}")

    # User growth
    users_last_30_days = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=30)
    ).count()

    users_last_7_days = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=7)
    ).count()

    users_total = User.objects.count()

    # Business growth
    businesses_last_30_days = Business.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()

    businesses_total = Business.objects.count()

    # Transaction volume
    transactions_last_30_days = Transaction.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()

    transactions_total = Transaction.objects.count()

    # Sales data
    sales_today = Transaction.objects.filter(
        transaction_type='sale',
        date=timezone.now().date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    sales_this_month = Transaction.objects.filter(
        transaction_type='sale',
        date__year=timezone.now().year,
        date__month=timezone.now().month
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'users_last_30_days': users_last_30_days,
        'users_last_7_days': users_last_7_days,
        'users_total': users_total,
        'businesses_last_30_days': businesses_last_30_days,
        'businesses_total': businesses_total,
        'transactions_last_30_days': transactions_last_30_days,
        'transactions_total': transactions_total,
        'sales_today': sales_today,
        'sales_this_month': sales_this_month,
    }

    print(f"   Analytics: {users_total} users, {businesses_total} businesses, {transactions_total} transactions")
    return render(request, 'admin_panel/analytics.html', context)


# ============================================================================
# SETTINGS
# ============================================================================

@login_required(login_url='/login/')
@staff_member_required(login_url='/login/')
def admin_settings(request):
    """Admin settings - platform configuration"""
    print(f"\n⚙️ ADMIN SETTINGS accessed by: {request.user.phone_number}")

    context = {
        'platform_name': 'BiasharaSmart Hub',
        'version': '1.0.0',
        'user': request.user,
    }
    return render(request, 'admin_panel/settings.html', context)


# ============================================================================
# TEST AND DEBUG ENDPOINTS
# ============================================================================

def admin_test(request):
    """Simple test view to check if admin panel is accessible without authentication"""
    return HttpResponse(f"""
    <html>
        <head>
            <title>Admin Test Page</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                h1 {{ color: #333; }}
                .success {{ color: green; font-weight: bold; }}
                .info {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .links {{ margin-top: 20px; }}
                .links a {{ display: inline-block; margin-right: 15px; color: #0066cc; }}
            </style>
        </head>
        <body>
            <h1>Admin Panel Test Page</h1>
            <p class="success">✅ Admin panel is accessible at this URL!</p>
            <div class="info">
                <h3>Debug Information:</h3>
                <p><strong>Time:</strong> {timezone.now()}</p>
                <p><strong>User authenticated:</strong> {request.user.is_authenticated}</p>
                <p><strong>User:</strong> {request.user}</p>
                <p><strong>Session key:</strong> {request.session.session_key}</p>
            </div>
            <div class="links">
                <p><strong>Test Links:</strong></p>
                <a href="/admin-panel/">➡️ Go to Admin Dashboard (requires login)</a><br>
                <a href="/admin-panel/health/">🏥 Health Check</a><br>
                <a href="/login/?next=/admin-panel/">🔑 Login with next parameter</a><br>
                <a href="/login/">🔐 Login page</a><br>
                <a href="/dashboard/">📊 Regular Dashboard</a>
            </div>
        </body>
    </html>
    """)


def admin_health_check(request):
    """Simple health check endpoint to verify admin panel is accessible"""
    data = {
        'status': 'ok',
        'message': 'Admin panel is accessible',
        'timestamp': timezone.now().isoformat(),
        'user_authenticated': request.user.is_authenticated,
        'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
    }
    return HttpResponse(json.dumps(data, indent=2), content_type='application/json')


def clear_session(request):
    """Utility view to clear session (for debugging)"""
    request.session.flush()
    return HttpResponse("Session cleared. <a href='/admin-panel/'>Go to admin panel</a>")

@staff_member_required
def customers_view(request):
    return render(request, 'admin_panel/customers.html')

@staff_member_required
def suppliers_view(request):
    return render(request, 'admin_panel/suppliers.html')

@staff_member_required
def pos_view(request):
    return render(request, 'admin_panel/pos.html')