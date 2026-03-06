"""
Production settings - extends base settings.
"""
import dj_database_url
from .base import *

# SECURITY
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# Validate SECRET_KEY
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY or SECRET_KEY.startswith('django-insecure'):
    raise ValueError("DJANGO_SECRET_KEY must be set to a secure value in production")

ALLOWED_HOSTS = [host for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if host]

# Si se pasa CSRF_TRUSTED_ORIGINS explícitamente, se usa; si no, se deriva de ALLOWED_HOSTS
_csrf_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [o for o in _csrf_env.split(',') if o]
else:
    CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS if h]

# CORS settings - restrictive in production (optional)
cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin for origin in cors_origins.split(',') if origin]

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Database - PostgreSQL for production
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    raise ValueError("DATABASE_URL environment variable is required in production")

# Override cache to use database instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

# Use database-backed sessions instead of Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Disable Celery in production (requires Redis)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Sentry error tracking
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='production',
    )

# Logging
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
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
