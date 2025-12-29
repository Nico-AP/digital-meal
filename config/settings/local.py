from .base import *
from .ckeditor_configs import CKEDITOR_5_CONFIGS
import os
import ddm.core


ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split()


# DEBUG
# ------------------------------------------------------------------------------
DEBUG = True

SITE_ID = 1


# DATABASE
# ------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dm.sqlite',
    }
}


# E-MAIL SETTINGS
# ------------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# DDM SETTINGS
# ------------------------------------------------------------------------------
WEBPACK_LOADER = {
    'DDM_UPLOADER': {
        'CACHE': True,
        'BUNDLE_DIR_NAME': 'ddm_core/frontend/uploader/',
        'STATS_FILE': os.path.join(
            os.path.dirname(ddm.core.__file__),
            'static/ddm_core/frontend/uploader/webpack-stats.json'
        ),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map']
    },
    'DDM_QUESTIONNAIRE': {
        'CACHE': True,
        'BUNDLE_DIR_NAME': 'ddm_core/frontend/questionnaire/',
        'STATS_FILE': os.path.join(
            os.path.dirname(ddm.core.__file__),
            'static/ddm_core/frontend/questionnaire/webpack-stats.json'
        ),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map']
    }
}

DDM_SETTINGS = {
    'EMAIL_PERMISSION_CHECK':  r'.*(\.|@).*\.ch$',
}


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
        'json': {
            '()': 'digital_meal.logging.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024*1024*15,
            'formatter': 'verbose',
        },
        'portability_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'portability.log'),
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'maxBytes': 1024 * 1024 * 15,
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'root': {
            'handlers': ['file', 'error_file'],
            'level': 'WARNING'
        },
        'digital_meal': {
            'handlers': ['file', 'error_file', 'console'],
            'propagate': False,
            'level': 'INFO',
        },
        'digital_meal.portability': {
            'handlers': ['portability_file', 'error_file', 'console'],
            'propagate': False,
            'level': 'INFO',
        }
    }
}
