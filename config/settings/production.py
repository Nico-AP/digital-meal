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
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024*1024*15,
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'maxBytes': 1024*1024*15,
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': False,
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['file', 'error_file', 'mail_admins'],
            'propagate': False,
            'level': 'ERROR',
        },
        'digital_meal' : {
            'handlers': ['file', 'error_file', 'mail_admins'],
            'propagate': False,
            'level': 'ERROR',
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
