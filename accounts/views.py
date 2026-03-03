from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, logout, authenticate, login as auth_login
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Count, Q, F, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, generics, filters
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
import json
import logging
from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.utils import timezone
from datetime import date, datetime, timedelta

from accounts.logger import log as syslog
from accounts.models import SystemLog
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    OTPVerificationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    AdminUserSerializer,
)
from .models import User
from businesses.models import Business
from notifications.tasks import send_sms_otp

logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================================================
# API VIEWS
# ============================================================================

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info(f"Registration attempt with data: {request.data}")
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Registration validation errors: {serializer.errors}")
            syslog('warning', 'auth',
                   f'Failed registration attempt',
                   f'Phone: {request.data.get("phone_number", "—")}  |  Errors: {serializer.errors}',
                   request=request)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        logger.info(f"User created: {user.id} - {user.phone_number}")

        syslog('success', 'auth',
               f'New user registered: {user.get_full_name() or user.username}',
               f'Phone: {user.phone_number}  |  Plan: {user.subscription_plan}  |  ID: {user.id}',
               user=user, request=request)

        otp = user.generate_otp()
        try:
            send_sms_otp(user.phone_number, otp)
            logger.info(f"OTP sent to {user.phone_number}")
        except Exception as e:
            logger.error(f"Failed to send OTP: {e}")
            syslog('error', 'auth',
                   f'OTP SMS delivery failed for {user.phone_number}',
                   str(e), user=user, request=request)

        return Response({
            'user_id': user.id,
            'phone_number': user.phone_number,
            'message': 'User created successfully. Please verify OTP sent to your phone.'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone = request.data.get('phone_number', '—')
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            syslog('warning', 'auth',
                   f'Failed API login attempt',
                   f'Phone: {phone}  |  Errors: {serializer.errors}',
                   request=request)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        syslog('info', 'auth',
               f'User logged in (API): {user.get_full_name() or user.username}',
               f'Phone: {user.phone_number}  |  ID: {user.id}',
               user=user, request=request)

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'phone_number': user.phone_number,
            'is_verified': user.is_phone_verified
        })


class OTPVerificationView(generics.GenericAPIView):
    serializer_class = OTPVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone = request.data.get('phone_number', '—')
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            syslog('warning', 'auth',
                   f'Failed OTP verification for {phone}',
                   f'Errors: {serializer.errors}',
                   request=request)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        user.is_phone_verified = True
        user.save()

        syslog('success', 'auth',
               f'Phone verified: {user.get_full_name() or user.username}',
               f'Phone: {user.phone_number}  |  ID: {user.id}',
               user=user, request=request)

        request.session.flush()
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Phone number verified successfully',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'phone_number': user.phone_number
        })


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def get_object(self):
        return self.request.user


class ResendOTPView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        try:
            user = User.objects.get(phone_number=phone_number)
            otp = user.generate_otp()
            send_sms_otp(user.phone_number, otp)
            syslog('info', 'auth',
                   f'OTP resent to {phone_number}',
                   f'User ID: {user.id}',
                   user=user, request=request)
            return Response({'message': 'OTP resent successfully'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminUserListView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['phone_number', 'first_name', 'last_name', 'username']
    ordering_fields = ['date_joined', 'last_login', 'first_name']
    ordering = ['-date_joined']

    def get_queryset(self):
        return User.objects.all().annotate(
            businesses_count=Count('businesses', distinct=True)
        ).order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        return User.objects.all().annotate(
            businesses_count=Count('businesses', distinct=True)
        )

    def perform_destroy(self, instance):
        if instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You cannot delete your own account.")
        syslog('warning', 'admin',
               f'User account deleted: {instance.get_full_name() or instance.username}',
               f'Deleted by: {self.request.user.username}  |  Target ID: {instance.id}',
               user=self.request.user, request=self.request)
        instance.delete()


class UpdateSubscriptionView(generics.UpdateAPIView):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()

    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        plan = request.data.get('plan')
        status_val = request.data.get('status')
        end = request.data.get('end_date')

        old_plan = user.subscription_plan

        if plan: user.subscription_plan = plan
        if status_val: user.subscription_status = status_val

        if end:
            try:
                user.subscription_end = datetime.strptime(end, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
        else:
            user.subscription_end = None

        user.save()
        syslog('info', 'admin',
               f'Subscription updated: {user.get_full_name() or user.username}',
               f'Plan: {old_plan} → {user.subscription_plan} | Status: {user.subscription_status}',
               user=request.user, request=request)

        return Response({
            'id': user.id,
            'plan': user.subscription_plan,
            'status': user.subscription_status,
            'end_date': user.subscription_end.isoformat() if user.subscription_end else '',
        })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def logs_list(request):
    level = request.GET.get('level')
    source = request.GET.get('source')
    date_val = request.GET.get('date')
    search = request.GET.get('search')

    qs = SystemLog.objects.select_related('user').all()

    if level and level != 'all': qs = qs.filter(level=level)
    if source and source != 'all': qs = qs.filter(source=source)
    if date_val: qs = qs.filter(timestamp__date=date_val)
    if search:
        qs = qs.filter(Q(message__icontains=search) | Q(detail__icontains=search))

    today = timezone.now().date()
    today_qs = SystemLog.objects.filter(timestamp__date=today)

    results = []
    for log in qs[:500]:
        results.append({
            'id': log.id,
            'level': log.level,
            'source': log.source,
            'message': log.message,
            'detail': log.detail,
            'timestamp': log.timestamp.isoformat(),
            'user': log.user.get_full_name() if log.user else None,
            'ip': log.ip,
        })

    return Response({
        'results': results,
        'stats': {
            'total_today': today_qs.count(),
            'errors': today_qs.filter(level='error').count(),
            'warnings': today_qs.filter(level='warning').count(),
            'info': today_qs.filter(level='info').count(),
        }
    })


# ============================================================================
# HTML PAGE VIEWS
# ============================================================================

def login_page(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '').strip()

        user = authenticate(request, phone_number=phone_number, password=password)

        if user is not None:
            if not user.is_active:
                syslog('warning', 'auth', f'Login blocked — account inactive: {phone_number}', request=request)
                return redirect('/login/?error=account_inactive')

            request.session.flush()
            auth_login(request, user)

            syslog('info', 'auth', f'User logged in: {user.phone_number}', user=user, request=request)

            if next_url and next_url.startswith('/') and 'login' not in next_url:
                return redirect(next_url)
            return redirect('/admin-panel/' if user.is_staff or user.is_superuser else '/dashboard/')
        else:
            return redirect('/login/?error=invalid_credentials')

    return render(request, 'accounts/login.html', {'next': request.GET.get('next', '')})


def register_page(request):
    return render(request, 'accounts/register.html')


def verify_otp_page(request):
    return render(request, 'accounts/verify_otp.html', {'phone': request.GET.get('phone', '')})


@login_required(login_url='/login/')
def dashboard_page(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin-panel/')
    return render(request, 'accounts/dashboard.html', {'user': request.user})


@login_required(login_url='/login/')
def add_sale_page(request):
    return render(request, 'accounts/add_sale.html', {'user': request.user})


@login_required(login_url='/login/')
def add_expense_page(request):
    return render(request, 'accounts/add_expense.html', {'user': request.user})


@login_required(login_url='/login/')
def inventory_page(request):
    return render(request, 'accounts/inventory.html', {'user': request.user})


@login_required(login_url='/login/')
def transactions_page(request):
    return render(request, 'accounts/transactions.html', {'user': request.user})


@login_required(login_url='/login/')
def analytics_page(request):
    return render(request, 'accounts/analytics.html', {'user': request.user})


@login_required(login_url='/login/')
def reports_page(request):
    return render(request, 'accounts/reports.html', {'user': request.user})


@login_required(login_url='/login/')
def alerts_page(request):
    return render(request, 'accounts/alerts.html', {'user': request.user})


@login_required(login_url='/login/')
def business_page(request):
    return render(request, 'accounts/business.html', {'user': request.user})


@login_required(login_url='/login/')
def settings_page(request):
    user = request.user
    business = Business.objects.filter(owner=user).first()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'profile':
            user.username = request.POST.get('username', user.username).strip()
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip() or None
            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('settings')

        if form_type == 'password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            if user.check_password(current_password) and new_password:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully.')
            else:
                messages.error(request, 'Error updating password.')
            return redirect('settings')

        if form_type == 'business' and business:
            business.name = request.POST.get('business_name', business.name).strip()
            business.sector = request.POST.get('sector', business.sector)
            business.town = request.POST.get('town', business.town).strip()
            business.save()
            messages.success(request, 'Business information updated.')
            return redirect('settings')

    return render(request, 'accounts/settings.html', {
        'user': user,
        'business': business,
        'sector_choices': [('retail', 'Retail'), ('wholesale', 'Wholesale'), ('restaurant', 'Food'),
                           ('service', 'Service'), ('other', 'Other')]
    })


# ============================================================================
# AI CHAT — FULLY UPDATED FOR GEMINI 2.0
# ============================================================================

@login_required(login_url='/login/')
def chat_page(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin-panel/')
    return render(request, 'accounts/chat.html', {'user': request.user})


@login_required(login_url='/login/')
@login_required(login_url='/login/')
def chat_api(request):
    """Streaming AI endpoint with automatic model fallback when quota is exhausted."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body    = json.loads(request.body)
        message = body.get('message', '').strip()
        history = body.get('history', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    user         = request.user
    context_data = _build_user_context(user)

    system_prompt = f"""You are Biashara AI, a professional business assistant for BiasharaSmart Hub in Kenya.
You are helping {user.get_full_name() or user.username}.

## Real-Time Business Context:
{context_data}

## Guidelines:
- Always use KES for currency.
- Provide data-driven advice based on the context above.
- Be helpful and professional.
- Use Swahili or English based on the user's preference.
"""

    # Models tried in order — each has its own separate quota bucket.
    # gemini-1.5-flash-8b is the most generous free tier model.
    FALLBACK_MODELS = [
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b',
        'gemini-1.0-pro',
    ]

    def _is_quota_error(exc):
        """Return True if the exception is a 429 / RESOURCE_EXHAUSTED quota error."""
        msg = str(exc)
        return '429' in msg or 'RESOURCE_EXHAUSTED' in msg or 'quota' in msg.lower()

    def stream_response():
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Build conversation history once — reuse across model attempts
        gemini_contents = []
        for h in history[-10:]:
            role = 'user' if h['role'].lower() == 'user' else 'model'
            gemini_contents.append(
                types.Content(role=role, parts=[types.Part(text=h['content'])])
            )
        gemini_contents.append(
            types.Content(role='user', parts=[types.Part(text=message)])
        )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1024,
            temperature=0.7,
        )

        last_error = None

        for model_name in FALLBACK_MODELS:
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=gemini_contents,
                    config=config,
                )
                # Stream succeeded — yield all chunks
                got_content = False
                for chunk in response:
                    if chunk.text:
                        got_content = True
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"

                if got_content:
                    yield "data: [DONE]\n\n"
                    syslog(
                        'info', 'api',
                        f'AI chat ({model_name}): {user.username}',
                        f'Prompt: {message[:50]}…',
                        user=user, request=request
                    )
                    return  # ← success, stop trying further models

            except Exception as exc:
                last_error = exc
                if _is_quota_error(exc):
                    # Log which model ran out and try the next one silently
                    syslog(
                        'warning', 'api',
                        f'Quota exhausted on {model_name}, trying next model.',
                        str(exc)[:120],
                        user=user, request=request
                    )
                    continue   # try next model
                else:
                    # Non-quota error (network, invalid key, etc.) — fail immediately
                    yield f"data: {json.dumps({'text': '⚠️ AI error. Please try again.'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

        # All models exhausted
        yield f"data: {json.dumps({'text': '⚠️ The AI assistant is temporarily unavailable due to high usage. Please try again in a few minutes.'})}\n\n"
        yield "data: [DONE]\n\n"
        syslog(
            'error', 'api',
            f'All Gemini models quota-exhausted for {user.username}',
            str(last_error)[:200],
            user=user, request=request
        )

    response = StreamingHttpResponse(stream_response(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def _build_user_context(user):
    """Pull real data from DB and format it for the AI."""
    from transactions.models import Transaction
    from inventory.models import Product
    from analytics.models import Alert

    today     = timezone.now().date()
    month_ago = today - timedelta(days=30)
    lines     = []

    # 1. Businesses
    businesses = Business.objects.filter(owner=user)
    if businesses.exists():
        lines.append("### Businesses:")
        for b in businesses:
            lines.append(f"  - {b.name} ({b.sector}) in {b.town}")

    # 2. Transactions
    try:
        txns     = Transaction.objects.filter(business__owner=user)
        sales    = txns.filter(transaction_type='sale',    date__gte=month_ago).aggregate(Sum('amount'))['amount__sum'] or 0
        expenses = txns.filter(transaction_type='expense', date__gte=month_ago).aggregate(Sum('amount'))['amount__sum'] or 0
        lines.append(
            f"\n### Last 30 Days: Sales KES {sales:,.0f} | Expenses KES {expenses:,.0f} | Profit KES {sales - expenses:,.0f}"
        )
    except Exception:
        lines.append("\n### Transactions: Could not load data.")

    # 3. Inventory
    try:
        products = Product.objects.filter(business__owner=user)
        if products.exists():
            low_stock = products.filter(quantity__lte=F('reorder_level'))
            if low_stock.exists():
                lines.append(
                    f"\n### Inventory: {products.count()} items. Low stock: " +
                    ", ".join([p.name for p in low_stock[:5]])
                )
            else:
                lines.append(f"\n### Inventory: {products.count()} items. Stock levels healthy.")
    except Exception:
        pass

    # 4. Active Alerts
    try:
        alerts = Alert.objects.filter(business__owner=user, is_resolved=False)
        if alerts.exists():
            lines.append("\n### Active Alerts: " + "; ".join([a.message for a in alerts[:3]]))
    except Exception:
        pass

    return "\n".join(lines) if lines else "No business data available yet."

@login_required(login_url='/login/')
def chat_debug(request):
    """
    Temporary diagnostic endpoint — visit /chat/debug/ in your browser.
    Remove this view once the issue is fixed.
    """
    import traceback
    results = {}

    # 1. Check API key exists
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    results['1_api_key'] = {
        'found': bool(api_key),
        'value': (api_key[:8] + '...' + api_key[-4:]) if api_key and len(api_key) > 12 else api_key,
    }

    if not api_key:
        return JsonResponse({'error': 'GEMINI_API_KEY missing', 'results': results})

    # 2. Try importing google.genai
    try:
        from google import genai
        from google.genai import types
        results['2_import'] = 'OK'
    except ImportError as e:
        results['2_import'] = f'FAILED: {e}'
        return JsonResponse({'error': 'Import failed', 'results': results})

    # 3. Try creating client
    try:
        client = genai.Client(api_key=api_key)
        results['3_client'] = 'OK'
    except Exception as e:
        results['3_client'] = f'FAILED: {e}'
        return JsonResponse({'error': 'Client init failed', 'results': results})

    # 4. Try each model with a simple ping
    MODELS = [
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b',
        'gemini-1.0-pro',
    ]
    results['4_models'] = {}
    for model_name in MODELS:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=[types.Content(role='user', parts=[types.Part(text='Say "OK" only.')])],
                config=types.GenerateContentConfig(max_output_tokens=10),
            )
            results['4_models'][model_name] = f'OK: {resp.text.strip()}'
        except Exception as e:
            err = str(e)
            if '429' in err or 'RESOURCE_EXHAUSTED' in err:
                results['4_models'][model_name] = 'QUOTA EXHAUSTED'
            elif 'not found' in err.lower() or '404' in err:
                results['4_models'][model_name] = 'MODEL NOT FOUND'
            else:
                results['4_models'][model_name] = f'ERROR: {err[:200]}'

    # 5. Test _build_user_context
    try:
        #from chat.views import _build_user_context   # adjust import path if needed
        ctx = _build_user_context(request.user)
        results['5_context'] = f'OK ({len(ctx)} chars)'
    except Exception as e:
        results['5_context'] = f'FAILED: {traceback.format_exc()}'

    return JsonResponse(results, json_dumps_params={'indent': 2})


def logout_view(request):
    if request.user.is_authenticated:
        syslog('info', 'auth', f'User logged out: {request.user.username}', user=request.user, request=request)
    logout(request)
    return redirect('/')