# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserProfile
import pyotp


# =========================
# USER REGISTRATION
# =========================
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'}, required=True)
    phone_number = serializers.CharField(max_length=15)
    subscription_plan = serializers.CharField(max_length=20, required=False, default='free')  # ← ADD

    class Meta:
        model = User
        fields = ('username', 'phone_number', 'email', 'password', 'password2',
                  'first_name', 'last_name', 'subscription_plan')  # ← ADD subscription_plan
        extra_kwargs = {
            'email': {'required': False, 'allow_null': True, 'allow_blank': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate_subscription_plan(self, value):
        valid = ['free', 'pro', 'enterprise']
        if value not in valid:
            return 'free'
        return value

    def validate(self, data):
        if data.get('password') != data.get('password2'):
            raise serializers.ValidationError({"password": "Passwords must match."})
        return data

    def validate_phone_number(self, value):
        if not value.startswith('254') or len(value) != 12:
            raise serializers.ValidationError(
                "Phone number must be in format 254XXXXXXXXX (e.g., 254712345678)"
            )
        return value

    def create(self, validated_data):
        validated_data.pop('password2', None)
        if not validated_data.get('email'):
            validated_data['email'] = None
        validated_data['otp_secret'] = pyotp.random_base32()

        # Set subscription end date based on plan
        from datetime import date, timedelta
        plan = validated_data.get('subscription_plan', 'free')
        if plan != 'free':
            validated_data['subscription_status'] = 'trial'
            validated_data['subscription_end'] = date.today() + timedelta(days=14)

        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

# =========================
# LOGIN WITH PHONE NUMBER
# =========================
class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        phone_number = data.get('phone_number')
        password = data.get('password')

        if phone_number and password:
            try:
                user = User.objects.get(phone_number=phone_number)
                if not user.check_password(password):
                    raise serializers.ValidationError("Unable to log in with provided credentials.")
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                data['user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError('Must include "phone_number" and "password".')

        return data


# =========================
# OTP VERIFICATION
# =========================
class OTPVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = User.objects.get(phone_number=data['phone_number'])
            if not user.verify_otp(data['otp']):
                raise serializers.ValidationError({'otp': 'Invalid OTP'})
            data['user'] = user
        except User.DoesNotExist:
            raise serializers.ValidationError({'phone_number': 'User not found'})
        return data


# =========================
# USER PROFILE SERIALIZERS
# =========================
class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'phone_number', 'email',
            'first_name', 'last_name', 'full_name',
            'is_staff', 'is_superuser', 'is_phone_verified',
            'date_joined', 'last_login', 'user_type'
        )
        read_only_fields = (
            'id', 'is_staff', 'is_superuser',
            'date_joined', 'last_login'
        )

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


# =========================
# ADMIN USER SERIALIZER
# =========================
class AdminUserSerializer(serializers.ModelSerializer):
    businesses_count = serializers.IntegerField(read_only=True, default=0)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'username', 'first_name', 'last_name',
            'email', 'is_active', 'is_staff', 'is_superuser',
            'is_phone_verified', 'date_joined', 'last_login',
            'businesses_count', 'password',
        ]
        read_only_fields = ['phone_number', 'date_joined', 'last_login']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance