"""Configuration pour la production - PostgreSQL"""
from decouple import config

DEBUG = False

# ======================================
# BASES DE DONNÉES PostgreSQL
# ======================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('AUTH_DB_NAME', default='gnexpress_auth'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    },
    'delivery_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DELIVERY_DB_NAME', default='gnexpress_delivery'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    },
    'market_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('MARKET_DB_NAME', default='gnexpress_market'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    },
    'marketplace_db': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('MARKETPLACE_DB_NAME', default='gnexpress_marketplace'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    },
}

# Sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')
