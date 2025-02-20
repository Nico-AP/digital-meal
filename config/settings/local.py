from .base import *
import os
import ddm.core


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


# DDM SETTINGS
# ------------------------------------------------------------------------------
WEBPACK_LOADER = {
    'DEFAULT': {
        'CACHE': not DEBUG,
        'BUNDLE_DIR_NAME': 'core/vue/',
        'STATS_FILE': os.path.join(
            os.path.dirname(ddm.core.__file__),
            'static/ddm_core/vue/webpack-stats.json'
        ),
        'POLL_INTERVAL': 0.1,  # Adjust as needed
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map'],
    }
}

DDM_SETTINGS = {
    'EMAIL_PERMISSION_CHECK':  r'.*(\.|@).*\.ch$',
}
