"""Configuration pour le développement - SQLite"""

DEBUG = True

# Autoriser toutes les origines en développement (évite les problèmes CORS)
CORS_ALLOW_ALL_ORIGINS = True

# Affichage des requêtes SQL en console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}
