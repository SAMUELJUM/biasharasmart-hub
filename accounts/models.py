# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import UserManager
import pyotp


class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=32, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    has_seen_onboarding = models.BooleanField(default=False)

    USER_TYPE_CHOICES = (
        ('owner', 'Business Owner'),
        ('staff', 'Staff Member'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='owner')

    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    subscription_plan   = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='free')
    subscription_status = models.CharField(max_length=20, default='active')
    subscription_end    = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'email']

    objects = UserManager()

    def generate_otp(self):
        if not self.otp_secret:
            self.otp_secret = pyotp.random_base32()
            self.save(update_fields=['otp_secret'])
        totp = pyotp.TOTP(self.otp_secret, interval=300)
        return totp.now()

    def verify_otp(self, otp):
        if not self.otp_secret:
            return False
        totp = pyotp.TOTP(self.otp_secret, interval=300)
        return totp.verify(otp)

    def __str__(self):
        return f'{self.phone_number}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    preferred_language = models.CharField(
        max_length=10,
        choices=[('en', 'English'), ('sw', 'Swahili')],
        default='en'
    )
    notification_preferences = models.JSONField(default=dict)

    class Meta:
        db_table = 'user_profiles'

    def __str__(self):
        return f'Profile of {self.user.phone_number}'


# ── SystemLog is TOP-LEVEL, NOT inside UserProfile ──
class SystemLog(models.Model):
    LEVEL_CHOICES = [
        ('error',   'Error'),
        ('warning', 'Warning'),
        ('info',    'Info'),
        ('success', 'Success'),
        ('debug',   'Debug'),
    ]
    SOURCE_CHOICES = [
        ('auth',         'Auth'),
        ('api',          'API'),
        ('transactions', 'Transactions'),
        ('inventory',    'Inventory'),
        ('system',       'System'),
        ('admin',        'Admin'),
    ]

    level     = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    source    = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='system')
    message   = models.CharField(max_length=500)
    detail    = models.TextField(blank=True, default='')
    user      = models.ForeignKey(
                    User, null=True, blank=True,
                    on_delete=models.SET_NULL,
                    related_name='systemlog'
                )
    ip        = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'[{self.level.upper()}] {self.source} — {self.message}'