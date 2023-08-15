from .base import *


ALLOWED_HOSTS = ['127.0.0.1']


# DEBUG
# ------------------------------------------------------------------------------
DEBUG = True


# DATABASE
# ------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'datadlab.sqlite',
    }
}


# DDM API SETTINGS
# ------------------------------------------------------------------------------
DDM_PARTICIPANT_ENDPOINT = 'http://127.0.0.1:8000/participants'
DDM_DONATION_ENDPOINT = 'http://127.0.0.1:8000/donations'
DDM_API_TOKEN = 'e871604ddc52680e8f40a6e10923b2aa522fff77'
