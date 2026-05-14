"""
integrations/views.py
─────────────────────
Handles:
  1. Africa's Talking USSD callback  → /integrations/ussd/
  2. Africa's Talking WhatsApp webhook → /integrations/whatsapp/
"""

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from decimal import Decimal, InvalidOperation
import json
import re
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _normalise_phone(phone):
    """Normalise to 2547XXXXXXXX format."""
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    if phone.startswith('+'):
        phone = phone[1:]
    return phone


def _get_user_and_business(phone):
    """
    Look up User by phone_number and return (user, business) or (None, None).
    Returns the first active business for the user.
    """
    from accounts.models import User
    from businesses.models import Business

    phone = _normalise_phone(phone)
    try:
        user = User.objects.get(phone_number=phone)
        business = Business.objects.filter(owner=user).first()
        return user, business
    except User.DoesNotExist:
        return None, None


def _get_balance(business):
    """Total sales minus total expenses = net balance."""
    from transactions.models import Transaction
    sales = Transaction.objects.filter(
        business=business, transaction_type='sale'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    expenses = Transaction.objects.filter(
        business=business, transaction_type='expense'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return sales - expenses


def _recent_transactions(business, limit=5):
    from transactions.models import Transaction
    return Transaction.objects.filter(
        business=business
    ).order_by('-date', '-created_at')[:limit]


def _record_transaction(business, user, tx_type, amount, description=''):
    from transactions.models import Transaction
    return Transaction.objects.create(
        business=business,
        transaction_type=tx_type,
        amount=Decimal(str(amount)),
        description=description or f'{tx_type.title()} via {"USSD" if description == "" else "WhatsApp"}',
        date=timezone.now().date(),
        created_by=user,
    )


# ─────────────────────────────────────────────────────────────
# USSD Handler
# ─────────────────────────────────────────────────────────────
#
# Africa's Talking sends POST with:
#   sessionId, phoneNumber, networkCode, serviceCode, text
#
# text is cumulative input separated by *
# e.g. first request: text=""
#      after pressing 1: text="1"
#      after pressing 500: text="1*500"
#
# Respond with:
#   CON <message>   → continue session (show next menu)
#   END <message>   → end session

@csrf_exempt
def ussd_callback(request):
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    session_id   = request.POST.get('sessionId', '')
    phone        = request.POST.get('phoneNumber', '')
    text         = request.POST.get('text', '')

    user, business = _get_user_and_business(phone)

    # Split cumulative input into steps
    parts = text.split('*') if text else ['']

    # ── Not registered ────────────────────────────────────────
    if not user or not business:
        return HttpResponse(
            'END Sorry, your phone number is not registered on BiasharaSmartHub. '
            'Please sign up at biasharasmarthub.com',
            content_type='text/plain'
        )

    step = len(parts)

    # ── Step 1: Main menu ─────────────────────────────────────
    if text == '':
        response = (
            f'CON Welcome to BiasharaSmartHub\n'
            f'{business.name}\n\n'
            f'1. Record Sale\n'
            f'2. Record Expense\n'
            f'3. Check Balance\n'
            f'4. Recent Transactions\n'
            f'0. Exit'
        )
        return HttpResponse(response, content_type='text/plain')

    choice = parts[0]

    # ── Exit ──────────────────────────────────────────────────
    if choice == '0':
        return HttpResponse('END Thank you for using BiasharaSmartHub. Goodbye!', content_type='text/plain')

    # ── Check Balance ─────────────────────────────────────────
    if choice == '3':
        balance = _get_balance(business)
        sales = Transaction_total(business, 'sale')
        expenses = Transaction_total(business, 'expense')
        return HttpResponse(
            f'END {business.name} Balance\n\n'
            f'Net Balance: KES {balance:,.2f}\n'
            f'Total Sales: KES {sales:,.2f}\n'
            f'Total Expenses: KES {expenses:,.2f}',
            content_type='text/plain'
        )

    # ── Recent Transactions ───────────────────────────────────
    if choice == '4':
        txns = _recent_transactions(business, limit=5)
        if not txns:
            return HttpResponse('END No transactions recorded yet.', content_type='text/plain')
        lines = [f'{business.name} - Last 5 Transactions\n']
        for t in txns:
            symbol = '+' if t.transaction_type == 'sale' else '-'
            lines.append(f'{symbol}KES {t.amount:,.0f} {t.date.strftime("%d/%m")}')
        return HttpResponse('END ' + '\n'.join(lines), content_type='text/plain')

    # ── Record Sale ───────────────────────────────────────────
    if choice == '1':
        if step == 1:
            return HttpResponse('CON Enter sale amount (KES):', content_type='text/plain')
        if step == 2:
            return HttpResponse('CON Enter description (or 0 to skip):', content_type='text/plain')
        if step == 3:
            try:
                amount = Decimal(parts[1])
                desc = parts[2] if parts[2] != '0' else 'Sale via USSD'
                _record_transaction(business, user, 'sale', amount, desc)
                balance = _get_balance(business)
                return HttpResponse(
                    f'END Sale recorded!\n\n'
                    f'Amount: KES {amount:,.2f}\n'
                    f'Description: {desc}\n'
                    f'New Balance: KES {balance:,.2f}',
                    content_type='text/plain'
                )
            except (InvalidOperation, IndexError):
                return HttpResponse('END Invalid amount. Please try again.', content_type='text/plain')

    # ── Record Expense ────────────────────────────────────────
    if choice == '2':
        if step == 1:
            return HttpResponse('CON Enter expense amount (KES):', content_type='text/plain')
        if step == 2:
            return HttpResponse('CON Enter description (or 0 to skip):', content_type='text/plain')
        if step == 3:
            try:
                amount = Decimal(parts[1])
                desc = parts[2] if parts[2] != '0' else 'Expense via USSD'
                _record_transaction(business, user, 'expense', amount, desc)
                balance = _get_balance(business)
                return HttpResponse(
                    f'END Expense recorded!\n\n'
                    f'Amount: KES {amount:,.2f}\n'
                    f'Description: {desc}\n'
                    f'New Balance: KES {balance:,.2f}',
                    content_type='text/plain'
                )
            except (InvalidOperation, IndexError):
                return HttpResponse('END Invalid amount. Please try again.', content_type='text/plain')

    return HttpResponse('END Invalid option. Please try again.', content_type='text/plain')


def Transaction_total(business, tx_type):
    from transactions.models import Transaction
    return Transaction.objects.filter(
        business=business, transaction_type=tx_type
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')


# ─────────────────────────────────────────────────────────────
# WhatsApp Bot Handler
# ─────────────────────────────────────────────────────────────
#
# Africa's Talking sends POST with JSON body:
# {
#   "from": "2547XXXXXXXX",
#   "text": "I sold 3 bags of maize at 500 each",
#   "to": "shortcode"
# }

@csrf_exempt
def whatsapp_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Twilio sends form-encoded POST data
    # Fields: From=whatsapp:+254..., Body=message text
    phone   = request.POST.get('From', '') or request.POST.get('from', '')
    message = request.POST.get('Body', '') or request.POST.get('text', '')

    # Strip whatsapp: prefix if present
    phone = phone.replace('whatsapp:', '').strip()
    message = message.strip()

    if not phone or not message:
        return JsonResponse({'error': 'Missing fields'}, status=400)

    user, business = _get_user_and_business(phone)

    if not user or not business:
        reply = (
            "Sorry, your number is not registered on BiasharaSmartHub. "
            "Please sign up at biasharasmarthub.com to get started."
        )
        _send_whatsapp(phone, reply)
        return JsonResponse({'status': 'sent'})

    reply = _process_whatsapp_message(message, user, business)
    _send_whatsapp(phone, reply)
    return JsonResponse({'status': 'sent'})


def _process_whatsapp_message(message, user, business):
    """
    Route the message to the right handler:
    - Sale/expense recording
    - Balance check
    - AI summary (Claude API)
    - Help
    """
    msg_lower = message.lower().strip()

    # ── Balance check ─────────────────────────────────────────
    if any(k in msg_lower for k in ['balance', 'how much', 'net', 'profit']):
        return _whatsapp_balance(business)

    # ── Recent transactions ───────────────────────────────────
    if any(k in msg_lower for k in ['recent', 'last', 'history', 'transactions', 'show me']):
        return _whatsapp_recent(business)

    # ── Sale recording ────────────────────────────────────────
    if any(k in msg_lower for k in ['sold', 'sale', 'received', 'income', 'earned']):
        return _whatsapp_record_sale(message, user, business)

    # ── Expense recording ─────────────────────────────────────
    if any(k in msg_lower for k in ['spent', 'expense', 'paid', 'bought', 'cost', 'purchase']):
        return _whatsapp_record_expense(message, user, business)

    # ── AI summary ────────────────────────────────────────────
    if any(k in msg_lower for k in ['summary', 'summarize', 'report', 'analyse', 'analyze', 'how is my business', 'how am i doing']):
        return _whatsapp_ai_summary(business)

    # ── Help ──────────────────────────────────────────────────
    if any(k in msg_lower for k in ['help', 'hi', 'hello', 'start', 'menu']):
        return _whatsapp_help(business)

    # ── Default: send to AI ───────────────────────────────────
    return _whatsapp_ai_query(message, user, business)


def _whatsapp_help(business):
    return (
        f"👋 Welcome to BiasharaSmartHub!\n"
        f"Business: *{business.name}*\n\n"
        f"Here's what you can do:\n\n"
        f"💰 *Record a sale*\n"
        f"→ \"I sold 5 bags of sugar at 200 each\"\n\n"
        f"💸 *Record an expense*\n"
        f"→ \"I spent 1500 on transport\"\n\n"
        f"📊 *Check balance*\n"
        f"→ \"What's my balance?\"\n\n"
        f"📋 *Recent transactions*\n"
        f"→ \"Show recent transactions\"\n\n"
        f"🤖 *AI business summary*\n"
        f"→ \"Summarize my business this week\""
    )


def _whatsapp_balance(business):
    balance = _get_balance(business)
    sales   = Transaction_total(business, 'sale')
    expenses = Transaction_total(business, 'expense')
    emoji = '📈' if balance >= 0 else '📉'
    return (
        f"{emoji} *{business.name} Balance*\n\n"
        f"Net Balance: *KES {balance:,.2f}*\n"
        f"Total Sales: KES {sales:,.2f}\n"
        f"Total Expenses: KES {expenses:,.2f}"
    )


def _whatsapp_recent(business):
    txns = _recent_transactions(business, limit=7)
    if not txns:
        return "No transactions recorded yet. Send a message like \"I sold 500 worth of goods\" to get started."
    lines = [f"📋 *{business.name} — Recent Transactions*\n"]
    for t in txns:
        symbol = '💰' if t.transaction_type == 'sale' else '💸'
        lines.append(f"{symbol} KES {t.amount:,.0f} — {t.description or t.transaction_type.title()} ({t.date.strftime('%d %b')})")
    return '\n'.join(lines)


def _whatsapp_record_sale(message, user, business):
    amount = _extract_amount(message)
    if not amount:
        return (
            "I couldn't find an amount in your message. Try:\n"
            "\"I sold goods worth 2500\" or\n"
            "\"Received 1200 from customer\""
        )
    desc = message[:100]
    _record_transaction(business, user, 'sale', amount, f'WhatsApp: {desc}')
    balance = _get_balance(business)
    return (
        f"✅ *Sale Recorded!*\n\n"
        f"Amount: KES {amount:,.2f}\n"
        f"Description: {desc}\n"
        f"New Balance: *KES {balance:,.2f}*"
    )


def _whatsapp_record_expense(message, user, business):
    amount = _extract_amount(message)
    if not amount:
        return (
            "I couldn't find an amount in your message. Try:\n"
            "\"I spent 500 on transport\" or\n"
            "\"Bought supplies for 3000\""
        )
    desc = message[:100]
    _record_transaction(business, user, 'expense', amount, f'WhatsApp: {desc}')
    balance = _get_balance(business)
    return (
        f"✅ *Expense Recorded!*\n\n"
        f"Amount: KES {amount:,.2f}\n"
        f"Description: {desc}\n"
        f"New Balance: *KES {balance:,.2f}*"
    )


def _extract_amount(text):
    """Extract first number from text. Handles: 500, 1,500, 1500.00, KES 500"""
    text = text.replace(',', '')
    matches = re.findall(r'\d+(?:\.\d+)?', text)
    for m in matches:
        try:
            val = Decimal(m)
            if val > 0:
                return val
        except InvalidOperation:
            continue
    return None


def _whatsapp_ai_summary(business):
    """Generate AI business summary using Claude API."""
    from transactions.models import Transaction
    from django.utils import timezone
    import datetime

    # Get last 30 days data
    thirty_days_ago = timezone.now().date() - datetime.timedelta(days=30)
    txns = Transaction.objects.filter(
        business=business,
        date__gte=thirty_days_ago
    ).order_by('-date')

    sales_total    = txns.filter(transaction_type='sale').aggregate(t=Sum('amount'))['t'] or 0
    expense_total  = txns.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or 0
    sales_count    = txns.filter(transaction_type='sale').count()
    expense_count  = txns.filter(transaction_type='expense').count()
    net            = Decimal(str(sales_total)) - Decimal(str(expense_total))

    # Build summary prompt for Claude
    recent_txns_text = '\n'.join([
        f"- {t.transaction_type.upper()}: KES {t.amount} on {t.date} ({t.description or 'No description'})"
        for t in txns[:15]
    ])

    prompt = (
        f"You are a business advisor for a small Kenyan business called '{business.name}'.\n\n"
        f"Last 30 days summary:\n"
        f"- Total Sales: KES {sales_total:,} ({sales_count} transactions)\n"
        f"- Total Expenses: KES {expense_total:,} ({expense_count} transactions)\n"
        f"- Net Balance: KES {net:,}\n\n"
        f"Recent transactions:\n{recent_txns_text}\n\n"
        f"Give a brief, friendly business health summary in 3-4 sentences. "
        f"Mention if things look good or need attention. "
        f"Give 1-2 practical tips. Keep it under 150 words. Use simple English."
    )

    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            ai_text = result['content'][0]['text']

        return (
            f"🤖 *AI Business Summary — {business.name}*\n\n"
            f"📊 Last 30 Days:\n"
            f"Sales: KES {sales_total:,} | Expenses: KES {expense_total:,} | Net: KES {net:,}\n\n"
            f"{ai_text}"
        )

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        # Fallback: plain summary without AI
        trend = "positive" if net >= 0 else "negative"
        return (
            f"📊 *{business.name} — 30 Day Summary*\n\n"
            f"💰 Sales: KES {sales_total:,.2f} ({sales_count} transactions)\n"
            f"💸 Expenses: KES {expense_total:,.2f} ({expense_count} transactions)\n"
            f"📈 Net: KES {net:,.2f}\n\n"
            f"Your business is trending {trend}."
        )


def _whatsapp_ai_query(message, user, business):
    """Send any freeform question to Claude with business context."""
    balance = _get_balance(business)
    sales   = Transaction_total(business, 'sale')
    expenses = Transaction_total(business, 'expense')

    prompt = (
        f"You are a helpful business assistant for '{business.name}', a small Kenyan business.\n"
        f"Current financials: Sales KES {sales:,}, Expenses KES {expenses:,}, Net KES {balance:,}.\n\n"
        f"The owner asks: {message}\n\n"
        f"Answer helpfully and briefly (under 100 words). If it's a greeting, introduce yourself."
    )

    try:
        import urllib.request

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01',
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['content'][0]['text']

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return _whatsapp_help(business)


def _send_whatsapp(phone, message):
    """Send WhatsApp message via Twilio."""
    from django.conf import settings

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token  = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

    if not account_sid or not auth_token:
        logger.warning("Twilio credentials not configured. Message not sent.")
        logger.info(f"Would send to {phone}: {message}")
        return

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        to_number = f'whatsapp:+{_normalise_phone(phone)}'
        client.messages.create(
            from_=from_number,
            to=to_number,
            body=message,
        )
        logger.info(f"WhatsApp sent to {phone}")
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")