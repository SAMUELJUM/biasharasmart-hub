from celery import shared_task
import random

@shared_task
def send_sms_otp(phone_number, otp):
    """
    Send OTP via SMS (mock implementation for development)
    In production, this would integrate with Africa's Talking or similar
    """
    print(f"Sending OTP {otp} to {phone_number}")
    # In production, you'd call your SMS gateway here
    return True

@shared_task
def send_whatsapp_message(phone_number, message):
    """Send WhatsApp message (mock implementation)"""
    print(f"Sending WhatsApp to {phone_number}: {message}")
    return True

@shared_task
def send_email_notification(email, subject, message):
    """Send email notification (mock implementation)"""
    print(f"Sending email to {email}: {subject} - {message}")
    return True