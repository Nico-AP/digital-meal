from .base import *
from .ckeditor_configs import CKEDITOR_5_CONFIGS
import os

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split()

SITE_ID = 1

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = False


# SECURITY SETTINGS
# ------------------------------------------------------------------------------
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

SECURE_HSTS_SECONDS = 3600
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# LOGGING
# ------------------------------------------------------------------------------
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            'class': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'errors.log'),
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'security.log'),
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 10,
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': False,
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        '': {
            'handlers': ['file', 'error_file', 'console', 'mail_admins'],
            'level': 'WARNING'
        },
        'django': {
            'handlers': ['file', 'error_file', 'mail_admins', 'console'],
            'propagate': False,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins', 'console'],
            'propagate': False,
            'level': 'ERROR',
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins', 'console'],
            'propagate': False,
            'level': 'WARNING',
        },
        'digital_meal' : {
            'handlers': ['file', 'error_file', 'mail_admins', 'console'],
            'propagate': False,
            'level': 'INFO',
        }
    }
}


# DATABASE
# ------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': os.environ['DJANGO_DB_HOST'],
        'NAME': os.environ['DJANGO_DB_NAME'],
        'USER': os.environ['DJANGO_DB_USER'],
        'PASSWORD': os.environ['DJANGO_DB_PW'],
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}
