from .settings import *
# File-backed database is required to prove concurrency behavior, unlike Django's shared in-memory test DB.
DATABASES['default']['TEST'] = {'NAME': str(BASE_DIR / 'test_bookbridge.sqlite3')}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
