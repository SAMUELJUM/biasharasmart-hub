import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import MpesaTransaction
from .mpesa import MpesaClient

logger = logging.getLogger(__name__)


@login_required(login_url='/login/')
def stk_push(request):
    """Initiate STK Push payment"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body         = json.loads(request.body)
        phone        = body.get('phone_number', '').strip()
        amount       = body.get('amount')
        business_id  = body.get('business_id')
        description  = body.get('description', 'Payment')
        reference    = body.get('reference', 'BiasharaSmart')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Validate
    if not phone or not amount or not business_id:
        return JsonResponse({'error': 'phone_number, amount and business_id are required'}, status=400)

    try:
        from businesses.models import Business
        business = Business.objects.get(id=business_id, owner=request.user)
    except Exception:
        return JsonResponse({'error': 'Business not found'}, status=404)

    # Get callback URL
    callback_url = settings.MPESA_CALLBACK_URL
    if not callback_url:
        return JsonResponse({'error': 'MPESA_CALLBACK_URL not configured. Start ngrok first.'}, status=500)

    try:
        client   = MpesaClient()
        response = client.stk_push(
            phone_number      = phone,
            amount            = amount,
            account_reference = reference,
            description       = description,
            callback_url      = callback_url,
        )

        logger.info(f'STK Push response: {response}')

        if response.get('ResponseCode') == '0':
            # Save pending transaction
            mpesa_txn = MpesaTransaction.objects.create(
                business            = business,
                phone_number        = phone,
                amount              = amount,
                description         = description,
                account_reference   = reference,
                merchant_request_id = response.get('MerchantRequestID', ''),
                checkout_request_id = response.get('CheckoutRequestID', ''),
                status              = 'pending',
            )
            return JsonResponse({
                'success':            True,
                'message':            'STK Push sent. Check your phone.',
                'checkout_request_id': mpesa_txn.checkout_request_id,
                'merchant_request_id': mpesa_txn.merchant_request_id,
            })
        else:
            return JsonResponse({
                'success': False,
                'message': response.get('errorMessage') or response.get('ResponseDescription', 'STK Push failed'),
            }, status=400)

    except Exception as e:
        logger.error(f'STK Push error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def mpesa_callback(request):
    """
    Safaricom calls this URL after payment is completed/failed.
    Must be publicly accessible (use ngrok in development).
    """
    if request.method != 'POST':
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid method'})

    try:
        body = json.loads(request.body)
        logger.info(f'M-Pesa callback received: {body}')

        stk_callback = body['Body']['stkCallback']
        checkout_request_id  = stk_callback['CheckoutRequestID']
        merchant_request_id  = stk_callback['MerchantRequestID']
        result_code          = stk_callback['ResultCode']
        result_desc          = stk_callback['ResultDesc']

        try:
            mpesa_txn = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id
            )
        except MpesaTransaction.DoesNotExist:
            logger.error(f'MpesaTransaction not found: {checkout_request_id}')
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        if result_code == 0:
            # Payment successful — extract callback metadata
            metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            meta = {item['Name']: item.get('Value', '') for item in metadata}

            mpesa_txn.status               = 'success'
            mpesa_txn.mpesa_receipt_number = str(meta.get('MpesaReceiptNumber', ''))
            mpesa_txn.transaction_date     = str(meta.get('TransactionDate', ''))
            mpesa_txn.result_code          = result_code
            mpesa_txn.result_desc          = result_desc
            mpesa_txn.save()

            # Auto-create a sale transaction
            _create_sale_from_mpesa(mpesa_txn, meta)

        else:
            # Payment failed/cancelled
            status_map = {
                1:  'failed',
                17: 'cancelled',
                1032: 'cancelled',
            }
            mpesa_txn.status      = status_map.get(result_code, 'failed')
            mpesa_txn.result_code = result_code
            mpesa_txn.result_desc = result_desc
            mpesa_txn.save()
            logger.info(f'M-Pesa payment failed: {result_desc}')

    except Exception as e:
        logger.error(f'M-Pesa callback error: {e}')

    # Always return success to Safaricom
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


def _create_sale_from_mpesa(mpesa_txn, meta):
    """Auto-record a sale transaction after successful M-Pesa payment"""
    try:
        from transactions.models import Transaction
        from django.utils import timezone

        sale = Transaction.objects.create(
            business         = mpesa_txn.business,
            transaction_type = 'sale',
            amount           = mpesa_txn.amount,
            payment_method   = 'mpesa',
            description      = f'M-Pesa payment — {mpesa_txn.mpesa_receipt_number}',
            date             = timezone.now().date(),
        )
        mpesa_txn.sale_transaction = sale
        mpesa_txn.save(update_fields=['sale_transaction'])
        logger.info(f'Sale auto-created from M-Pesa: {sale.id}')

        # Send SMS confirmation
        _send_confirmation_sms(mpesa_txn)

    except Exception as e:
        logger.error(f'Failed to create sale from M-Pesa: {e}')


def _send_confirmation_sms(mpesa_txn):
    """Send SMS receipt to customer"""
    try:
        from notifications.tasks import send_sms
        msg = (
            f'Payment received: KES {mpesa_txn.amount:,.0f} '
            f'from {mpesa_txn.phone_number}. '
            f'Receipt: {mpesa_txn.mpesa_receipt_number}. '
            f'Thank you - {mpesa_txn.business.name}'
        )
        send_sms(mpesa_txn.phone_number, msg)
    except Exception as e:
        logger.error(f'SMS confirmation failed: {e}')


@login_required(login_url='/login/')
def stk_status(request, checkout_request_id):
    """Check payment status — called by frontend polling"""
    try:
        mpesa_txn = MpesaTransaction.objects.get(
            checkout_request_id=checkout_request_id,
            business__owner=request.user
        )
        return JsonResponse({
            'status':         mpesa_txn.status,
            'receipt_number': mpesa_txn.mpesa_receipt_number,
            'amount':         str(mpesa_txn.amount),
            'phone':          mpesa_txn.phone_number,
            'result_desc':    mpesa_txn.result_desc,
        })
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)


@login_required(login_url='/login/')
def mpesa_transactions(request):
    """List all M-Pesa transactions for the user's businesses"""
    txns = MpesaTransaction.objects.filter(
        business__owner=request.user
    ).select_related('business').order_by('-created_at')[:50]

    return JsonResponse({
        'results': [{
            'id':             t.id,
            'phone':          t.phone_number,
            'amount':         str(t.amount),
            'status':         t.status,
            'receipt':        t.mpesa_receipt_number,
            'description':    t.description,
            'business':       t.business.name,
            'created_at':     t.created_at.isoformat(),
        } for t in txns]
    })