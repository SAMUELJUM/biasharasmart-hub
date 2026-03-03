from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class PhoneNumberAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows login with phone number
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to get phone_number from kwargs or username
        phone_number = kwargs.get('phone_number') or username

        if phone_number is None or password is None:
            return None

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None