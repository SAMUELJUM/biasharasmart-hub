from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from accounts.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock
import pyotp

User = get_user_model()


class UserRegistrationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.valid_payload = {
            'username': 'testuser',
            'phone_number': '254712345678',
            'password': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }

    @patch('notifications.tasks.send_sms_otp')  # Mock the function directly, not .delay
    def test_user_registration(self, mock_send_sms):
        """Test user registration is successful"""
        mock_send_sms.return_value = None

        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)

        user = User.objects.get()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.phone_number, '254712345678')
        self.assertFalse(user.is_phone_verified)

        # Check that OTP was sent
        mock_send_sms.assert_called_once()
        # Check that it was called with phone number and OTP
        args, kwargs = mock_send_sms.call_args
        self.assertEqual(args[0], '254712345678')  # phone number
        self.assertTrue(len(args[1]) == 6)  # OTP should be 6 digits

    @patch('notifications.tasks.send_sms_otp')
    def test_duplicate_phone_registration(self, mock_send_sms):
        """Test registration with duplicate phone number fails"""
        mock_send_sms.return_value = None

        # Create first user
        response1 = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Try to create another with same phone
        response2 = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('notifications.tasks.send_sms_otp')
    def test_registration_without_required_fields(self, mock_send_sms):
        """Test registration fails without required fields"""
        mock_send_sms.return_value = None

        invalid_payload = {
            'username': 'testuser'
        }
        response = self.client.post(self.register_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('notifications.tasks.send_sms_otp')
    def test_registration_password_mismatch(self, mock_send_sms):
        """Test registration fails when passwords don't match"""
        mock_send_sms.return_value = None

        payload = self.valid_payload.copy()
        payload['password2'] = 'differentpassword'

        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', str(response.data))  # Check that error mentions password


class UserLoginTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/auth/login/'

        # Create a user with email set to None to avoid unique constraint
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='254712345678',
            password='testpass123',
            first_name='Test',
            last_name='User',
            email=None
        )
        # User needs to be verified to login with password
        self.user.is_phone_verified = True
        self.user.save()

    def test_user_login_success(self):
        """Test successful login with verified phone"""
        payload = {
            'phone_number': '254712345678',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, payload, format='json')

        # Print debug info if test fails
        if response.status_code != status.HTTP_200_OK:
            print(f"Login failed. Response: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user_id'], self.user.id)
        self.assertEqual(response.data['phone_number'], self.user.phone_number)
        self.assertTrue(response.data['is_verified'])

    def test_user_login_invalid_password(self):
        """Test login fails with invalid password"""
        payload = {
            'phone_number': '254712345678',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_nonexistent_user(self):
        """Test login fails with non-existent phone number"""
        payload = {
            'phone_number': '254700000000',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_missing_fields(self):
        """Test login fails with missing fields"""
        payload = {
            'phone_number': '254712345678'
            # Missing password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OTPVerificationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.verify_otp_url = '/api/auth/verify-otp/'

        # Create a user directly with OTP secret
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='254712345678',
            password='testpass123',
            first_name='Test',
            last_name='User',
            email=None
        )
        # Set OTP secret
        self.user.otp_secret = pyotp.random_base32()
        self.user.save()

    def test_otp_verification_success(self):
        """Test successful OTP verification"""
        # Generate OTP for testing
        otp = self.user.generate_otp()

        # Verify OTP
        verify_payload = {
            'phone_number': '254712345678',
            'otp': otp
        }
        verify_response = self.client.post(self.verify_otp_url, verify_payload, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        # Check that user is now verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_phone_verified)

    def test_otp_verification_invalid_otp(self):
        """Test OTP verification fails with invalid OTP"""
        # Verify with wrong OTP
        verify_payload = {
            'phone_number': '254712345678',
            'otp': '000000'  # Wrong OTP
        }
        verify_response = self.client.post(self.verify_otp_url, verify_payload, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check that user is still not verified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_phone_verified)

    def test_otp_verification_nonexistent_user(self):
        """Test OTP verification fails for non-existent user"""
        verify_payload = {
            'phone_number': '254700000000',
            'otp': '123456'
        }
        verify_response = self.client.post(self.verify_otp_url, verify_payload, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_400_BAD_REQUEST)


class UserModelTests(TestCase):
    """Tests for the User model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            phone_number='254712345678',
            password='testpass123',
            first_name='Test',
            last_name='User',
            email=None
        )

    def test_user_creation(self):
        """Test user is created correctly"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.phone_number, '254712345678')
        self.assertTrue(self.user.check_password('testpass123'))
        self.assertEqual(self.user.get_full_name(), 'Test User')

    def test_otp_generation_and_verification(self):
        """Test OTP generation and verification works"""
        # Generate OTP
        otp = self.user.generate_otp()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

        # Verify correct OTP
        self.assertTrue(self.user.verify_otp(otp))

        # Verify incorrect OTP
        self.assertFalse(self.user.verify_otp('000000'))

    def test_str_representation(self):
        """Test string representation"""
        expected = f"{self.user.username} ({self.user.phone_number})"
        self.assertEqual(str(self.user), expected)