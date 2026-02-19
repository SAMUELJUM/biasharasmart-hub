from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # This inherits all standard fields (username, password, email, etc.)
    # You can add custom fields here later (e.g., phone_number = models.CharField(max_length=15))
    pass