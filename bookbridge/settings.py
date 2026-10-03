import os
from datetime import timedelta
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('BOOKBRIDGE_DEBUG', '1') == '1'
SECRET_KEY = os.environ.get('BOOKBRIDGE_SECRET_KEY', 'local-development-only-bookbridge-change-before-hosting')
if not DEBUG and SECRET_KEY.startswith('local-development'):
    raise ImproperlyConfigured('Set BOOKBRIDGE_SECRET_KEY before running in production.')
ALLOWED_HOSTS = os.environ.get('BOOKBRIDGE_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'axes',
    'bridge.apps.BridgeConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'bridge.middleware.DatabaseBusyMiddleware',
    'axes.middleware.AxesMiddleware',
]
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

def positive_env(name, default):
    try:
        value = int(os.environ.get(name, default))
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be a positive integer.') from exc
    if value < 1:
        raise ImproperlyConfigured(f'{name} must be a positive integer.')
    return value

AXES_FAILURE_LIMIT = positive_env('BOOKBRIDGE_LOGIN_FAILURE_LIMIT', '5')
AXES_COOLOFF_TIME = timedelta(minutes=positive_env('BOOKBRIDGE_LOGIN_COOLOFF_MINUTES', '15'))
AXES_LOCKOUT_PARAMETERS = ['username']
AXES_HANDLER = 'bridge.security.AccountLoginHandler'
AXES_CLIENT_IP_CALLABLE = 'bridge.security.no_client_ip'
AXES_USERNAME_CALLABLE = 'bridge.security.login_username'
AXES_LOCKOUT_CALLABLE = 'bridge.security.login_locked_out'
AXES_RESET_ON_SUCCESS = True
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_SENSITIVE_PARAMETERS = ['username', 'ip_address', 'csrfmiddlewaretoken']
# AccountLoginHandler groups all browsers into one account counter. Rotating
# IPs, user agents or cookies cannot bypass it; avoid blocking a school's shared IP.
SILENCED_SYSTEM_CHECKS = ['axes.W006']
ROOT_URLCONF = 'bookbridge.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages', 'bridge.context_processors.navigation',
    ]},
}]
WSGI_APPLICATION = 'bookbridge.wsgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.environ.get('BOOKBRIDGE_DATABASE', str(BASE_DIR / 'db.sqlite3')),
    'OPTIONS': {'transaction_mode': 'IMMEDIATE', 'timeout': 20},
}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
CSRF_FAILURE_VIEW = 'bridge.views.csrf_failure'
SUPPORT_EMAIL = os.environ.get('BOOKBRIDGE_SUPPORT_EMAIL', '')
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Enable only behind a trusted proxy that strips client-supplied headers.
    if os.environ.get('BOOKBRIDGE_TRUST_PROXY') == '1':
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [x for x in os.environ.get('BOOKBRIDGE_CSRF_ORIGINS', '').split(',') if x]
