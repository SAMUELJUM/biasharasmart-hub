import base64
import requests
from datetime import datetime
from django.conf import settings


class MpesaClient:

    def __init__(self):
        self.env             = settings.MPESA_ENV
        self.consumer_key    = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode       = settings.MPESA_SHORTCODE
        self.passkey         = settings.MPESA_PASSKEY

        if self.env == 'sandbox':
            self.base_url = 'https://sandbox.safaricom.co.ke'
        else:
            self.base_url = 'https://api.safaricom.co.ke'

    def get_access_token(self):
        url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        response = requests.get(
            url,
            auth=(self.consumer_key, self.consumer_secret),
            timeout=30
        )
        response.raise_for_status()
        return response.json()['access_token']

    def get_timestamp(self):
        return datetime.now().strftime('%Y%m%d%H%M%S')

    def get_password(self, timestamp):
        raw = f'{self.shortcode}{self.passkey}{timestamp}'
        return base64.b64encode(raw.encode()).decode()

    def stk_push(self, phone_number, amount, account_reference, description, callback_url):
        """
        Trigger STK Push — sends payment prompt to customer's phone.
        phone_number format: 2547XXXXXXXX
        """
        token     = self.get_access_token()
        timestamp = self.get_timestamp()
        password  = self.get_password(timestamp)

        # Normalize phone number
        phone = str(phone_number).strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]

        url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password':          password,
            'Timestamp':         timestamp,
            'TransactionType':   'CustomerPayBillOnline',
            'Amount':            int(amount),
            'PartyA':            phone,
            'PartyB':            self.shortcode,
            'PhoneNumber':       phone,
            'CallBackURL':       callback_url,
            'AccountReference':  account_reference[:12],
            'TransactionDesc':   description[:20],
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return response.json()

    def stk_query(self, checkout_request_id):
        """Check the status of an STK Push request"""
        token     = self.get_access_token()
        timestamp = self.get_timestamp()
        password  = self.get_password(timestamp)

        url = f'{self.base_url}/mpesa/stkpushquery/v1/query'
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password':          password,
            'Timestamp':         timestamp,
            'CheckoutRequestID': checkout_request_id,
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return response.json()