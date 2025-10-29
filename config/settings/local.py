"""
Local development settings.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Database - SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS Settings - Allow all origins for local development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Additional apps for development
INSTALLED_APPS += [
    'django_extensions',  # Optional: Provides management commands like shell_plus
]

# Email backend - Console for local development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Add browsable API renderer for local development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',  # DRF web interface
]

print("[OK] Local development settings loaded")
print(f"[OK] DEBUG = {DEBUG}")
print(f"[OK] Database: SQLite ({DATABASES['default']['NAME']})")
