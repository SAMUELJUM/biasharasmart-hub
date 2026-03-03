import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
ALLOWED_HOSTS += ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.io']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',
    
    # Third-party apps
    'rest_framework',
    'corsheaders',
    'django_extensions',
    
    # Local apps
    'home',
    'accounts',
    'businesses',
    'transactions',
    'inventory',
    'analytics',
    'reports',
    'notifications',
    'integrations',
    'admin_panel',
    'mpesa',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.OnboardingMiddleware',

]

ROOT_URLCONF = 'biasharasmart_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'biasharasmart_hub.wsgi.application'

# Database
# Using SQLite for development as specified
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv('DB_NAME', 'db.sqlite3'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/admin-panel/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
]

# JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# Celery settings
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'

# Africa's Talking settings
AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY')
AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')

# Safaricom Daraja settings
SAFARICOM_CONSUMER_KEY = os.getenv('SAFARICOM_CONSUMER_KEY')
SAFARICOM_CONSUMER_SECRET = os.getenv('SAFARICOM_CONSUMER_SECRET')
SAFARICOM_ENVIRONMENT = 'sandbox'  # Change to 'production' for live
# M-Pesa Settings
MPESA_CONSUMER_KEY     = os.getenv('SAFARICOM_CONSUMER_KEY')
MPESA_CONSUMER_SECRET  = os.getenv('SAFARICOM_CONSUMER_SECRET')
MPESA_SHORTCODE        = os.getenv('MPESA_SHORTCODE', '174379')
MPESA_PASSKEY          = os.getenv('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
MPESA_ENV              = os.getenv('MPESA_ENV', 'sandbox')
MPESA_CALLBACK_URL     = os.getenv('MPESA_CALLBACK_URL', '')


AUTHENTICATION_BACKENDS = [
    'accounts.backends.PhoneNumberAuthBackend',  # Custom backend
    'django.contrib.auth.backends.ModelBackend',  # Default backend
]

# settings.py
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL_NAME = 'gemini-1.5-flash'
#ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')