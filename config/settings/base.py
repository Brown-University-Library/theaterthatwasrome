import math
import os

from django.core.exceptions import ImproperlyConfigured


def get_env_setting(setting):
    """Get the environment setting or return exception"""
    try:
        return os.environ[setting]
    except KeyError:
        error_msg = 'Set the %s env variable' % setting
        raise ImproperlyConfigured(error_msg.encode('utf8'))


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def positive_env_seconds(name: str, default: float) -> float:
    """
    Reads a finite, positive timeout in seconds from the environment.
    Called by: config.settings.base module initialization
    """
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be a positive number of seconds.') from exc
    if not math.isfinite(value) or value <= 0:
        raise ImproperlyConfigured(f'{name} must be a positive number of seconds.')
    return value


BDR_CONNECT_TIMEOUT = positive_env_seconds('ROME_BDR_CONNECT_TIMEOUT', 5.0)
BDR_READ_TIMEOUT = positive_env_seconds('ROME_BDR_READ_TIMEOUT', 10.0)

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'config.middleware.bdr_failure_middleware.BdrFailureMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.messages.context_processors.messages',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
            ]
        },
    },
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'crispy_forms',
    'markdown_deux',
    'pagedown',
    'rome_app',
)

## maximum session age: 1 day
SESSION_COOKIE_AGE = 86400

TIME_ZONE = 'America/New_York'

USE_TZ = True

ROOT_URLCONF = 'config.urls'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

STATIC_ROOT = os.path.normpath(os.path.join(BASE_DIR, 'assets'))

MEDIA_ROOT = os.path.normpath(os.path.join(BASE_DIR, 'media'))

CRISPY_TEMPLATE_PACK = 'bootstrap3'

MARKDOWN_DEUX_STYLES = {
    'default': {
        'extras': {
            'code-friendly': None,
            'footnotes': None,
        },
        'safe_mode': 'escape',
    },
}

LOG_DIR = get_env_setting('LOG_DIR')

## logging order of operations --------------------------------------
## django.request logger
##   │
##   ├─ Below ERROR? Stop.
##   │
##   └─ mail_admins handler
##        │
##        ├─ Below ERROR? Stop.
##        ├─ require_debug_false: DEBUG=True? Stop.
##        ├─ skip_handled_bdr_failure: Handled BDR outage? Stop.
##        │
##        └─ Send administrator email.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            # 'format': '%(asctime)s %(levelname)s %(message)s'
            'format': '[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'},
        'skip_handled_bdr_failure': {'()': 'rome_app.lib.bdr_failure.SkipHandledBdrFailure'},
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false', 'skip_handled_bdr_failure'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'log_file': {
            # 'level': 'DEBUG',
            'level': os.environ.get('LOG_LEVEL', 'INFO'),  # add LOG_LEVEL='DEBUG' to the .env file to see debug messages
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'rome.log'),
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            'handlers': ['null'],  # do nothing for disallowed hosts errors
            'propagate': False,
        },
        'rome': {
            'handlers': ['log_file'],
            'level': 'DEBUG',  # messages above this will get sent to the `log_file` handler
            'propagate': False,
        },
    },
}

TTWR_COLLECTION_PID = 'bdr:240509'  # ID: 621
