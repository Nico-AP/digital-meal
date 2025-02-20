from .base import *

ALLOWED_HOSTS = []


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
