from .base import *  # noqa

from decouple import config

DJANGO_ENV = config('DJANGO_ENV', default='development')

if DJANGO_ENV == 'production':
    from .production import *  # noqa
else:
    from .development import *  # noqa
