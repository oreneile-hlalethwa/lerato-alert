"""Lerato Alert – Django settings.

Every secret comes from environment variables (a local .env file in development,
Render's Environment tab in production). See .env.example.
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # .../Lerato/backend
FRONTEND_DIR = BASE_DIR.parent / 'frontned'                  # .../Lerato/frontned
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [x.strip() for x in os.getenv(name, default).split(',') if x.strip()]


DEBUG = env_bool('DEBUG', False)
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-insecure-key-change-me'
    else:
        raise ImproperlyConfigured('Set SECRET_KEY in the environment.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lerato.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lerato.wsgi.application'

# Database: Supabase Postgres via DATABASE_URL, or SQLite locally if it's not set.
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True, ssl_require=True)}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-za'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# Static files (Django admin) + the whole frontend served from the site root.
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
if FRONTEND_DIR.exists():
    WHITENOISE_ROOT = FRONTEND_DIR          # /, /alert/, /vault/pin.html ... come from frontned/
    WHITENOISE_INDEX_FILE = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS: only needed when the frontend runs on a different port (e.g. python -m http.server 5500).
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500')
CORS_ALLOW_HEADERS = ['accept', 'content-type', 'x-lerato-token']
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    CSRF_TRUSTED_ORIGINS.append('https://' + os.environ['RENDER_EXTERNAL_HOSTNAME'])

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],      # the app uses its own X-Lerato-Token header
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.ScopedRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '600/hour',
        'register': '20/hour',
        'alerts': '20/hour',
        'ai': '120/hour',
        'writes': '120/hour',
        'vault': '200/hour',
    },
}

# Behind Render's proxy, trust its HTTPS header and harden cookies.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'

# ---- Third-party services ----
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-5-5')

BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_SENDER_EMAIL = os.getenv('BREVO_SENDER_EMAIL', '')
BREVO_SENDER_NAME = os.getenv('BREVO_SENDER_NAME', 'Lerato Alert')
BREVO_SMS_SENDER = os.getenv('BREVO_SMS_SENDER', 'LeratoAlert')[:11]
SMS_ENABLED = env_bool('SMS_ENABLED', False)   # email only for now; set true once SMS credits are bought

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

# Cloudinary: private backup of vault evidence.
# Either the three separate keys, or one CLOUDINARY_URL (cloudinary://API_KEY:API_SECRET@CLOUD_NAME).
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
CLOUDINARY_URL = os.getenv('CLOUDINARY_URL', '')
VAULT_MAX_MB = int(os.getenv('VAULT_MAX_MB', '40'))
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # bigger uploads stream to a temp file

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'api': {'handlers': ['console'], 'level': 'INFO'}},
}