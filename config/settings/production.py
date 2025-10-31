"""
Production settings for deployment.
"""
from .base import *
import dj_database_url

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Database - PostgreSQL for production
# Railway/Render provide DATABASE_URL automatically
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# CORS Settings - Allow all for development (restrict later)
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
print(f"[DEBUG] CORS_ALLOWED_ORIGINS env var: '{cors_origins}'")

if cors_origins == '*' or not cors_origins:
    # Allow all origins for development using regex
    import re
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^http://localhost:\d+$",  # Local development (any port)
        r"^https://.*\.up\.railway\.app$",  # Railway backend
        r"^https://.*\.onrender\.com$",  # Render frontend
    ]
    CORS_ALLOW_ALL_ORIGINS = False  # Don't use wildcard
    CORS_ALLOWED_ORIGINS = []
    CORS_ALLOW_CREDENTIALS = False
    print(f"[OK] CORS: Using regex patterns for origins (credentials = False)")
else:
    # Specific origins only
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
    CORS_ALLOW_CREDENTIALS = True  # Can allow credentials with specific origins
    print(f"[OK] CORS: Specific origins: {CORS_ALLOWED_ORIGINS}, credentials = True")
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
print(f"[OK] CORS: Allow credentials: {CORS_ALLOW_CREDENTIALS}")

# Security Settings
# Note: Railway handles SSL termination, so SECURE_SSL_REDIRECT = False
SECURE_SSL_REDIRECT = False  # Railway provides HTTPS at edge
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static files (Whitenoise for production)
# Insert Whitenoise after CORS middleware (position 2) to avoid interfering with CORS
MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = []  # No additional static dirs in production (only app static files)

# Email backend - Production email service
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# Logging - Console only in production (Railway provides log aggregation)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

print("[OK] Production settings loaded")
print(f"[OK] DEBUG = {DEBUG}")
print("[OK] Database: PostgreSQL")
print("[OK] Logging: Console only (file logging disabled)")
