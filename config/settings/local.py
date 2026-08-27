from pathlib import Path

from .base import *
from .base import BASE_DIR

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(BASE_DIR).parent / 'rome.sqlite3',
    }
}


SECRET_KEY = '1234567890'
STATIC_URL = '/static/'

ALLOWED_HOSTS = ['*']
TTWR_COLLECTION_PID = (
    'test:5m6nkymr'  # TEMPORARILY-DISABLED -- overrides setting in base.py, which has the production-collection pid
)
