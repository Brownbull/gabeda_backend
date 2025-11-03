"""
Local development settings.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Database - SQLite for local development (PostgreSQL in production)
# Note: Production uses PostgreSQL. SQLite is used locally due to Windows psycopg3 auth issues.
import os
from pathlib import Path

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(__file__).resolve().parent.parent.parent / 'db.sqlite3',
    }
}

# Uncomment below to use PostgreSQL locally (requires psycopg3 and working Docker PostgreSQL)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'gabeda_db',
#         'USER': 'postgres',
#         'PASSWORD': 'gabeda_dev_password',
#         'HOST': '127.0.0.1',
#         'PORT': '5432',
#         'OPTIONS': {},
#     }
# }

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
db_engine = DATABASES['default']['ENGINE']
db_name = DATABASES['default'].get('NAME', DATABASES['default'].get('HOST', 'Unknown'))
print(f"[OK] Database: {db_engine.split('.')[-1].upper()} ({db_name})")
