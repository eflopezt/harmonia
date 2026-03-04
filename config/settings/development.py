"""
Development settings - extends base settings.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# CSRF settings for development (Codespaces, local, etc.)
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'https://localhost:8000',
    'http://127.0.0.1:8000',
    'https://127.0.0.1:8000',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
    'https://*.app.github.dev',
    'https://*.githubpreview.dev',
]

# Database - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Cache en memoria local (sin Redis) para desarrollo
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Usar sesiones en base de datos en lugar de cache
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Add django-debug-toolbar for development
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.common.CommonMiddleware') + 1,
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INTERNAL_IPS = []  # Toolbar desactivado temporalmente para demo

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Sentry in development
SENTRY_DSN = None
