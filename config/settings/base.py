import os

from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# APPLICATION DEFINITIONS
# ------------------------------------------------------------------------------
SECRET_KEY = os.environ['DJANGO_SECRET']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'taggit',
    'digital_meal.tool',
    'digital_meal.website',
    'digital_meal.reports',
    'digital_meal.portability',
    'cookie_consent',
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail.locales',
    'wagtail.contrib.simple_translation',
    'wagtail',
    'wagtailvideos',
    'wagtail_modeladmin',
    'qr_code',
    # DDM
    'ddm',
    'ddm.auth',
    'ddm.logging',
    'ddm.questionnaire',
    'ddm.datadonation',
    'ddm.participation',
    'ddm.projects',
    'ddm.core',
    'webpack_loader',
    'rest_framework',
    'rest_framework.authtoken',
    'django_ckeditor_5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'digital_meal.website.middleware.RestrictDDMMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'ddm.core.context_processors.add_ddm_version',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# INTERNATIONALIZATION
# ------------------------------------------------------------------------------
LANGUAGE_CODE = 'de'
TIME_ZONE = 'Europe/Zurich'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale'), ]

WAGTAILSIMPLETRANSLATION_SYNC_PAGE_TREE = True

WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [
    ('de', 'Deutsch')
]


# USER AUTHENTICATION AND PASSWORD VALIDATION
# ------------------------------------------------------------------------------
AUTH_USER_MODEL = 'tool.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'Digital Meal | '
ACCOUNT_FORMS = {'signup': 'digital_meal.tool.forms.SimpleSignupForm'}
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_MAX_EMAIL_ADDRESSES = 2

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LOGIN_REDIRECT_URL = '/tool/'
LOGOUT_REDIRECT_URL = '/'


# STATIC FILES
# ------------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles/')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')


# DEFAULT PRIMARY KEY FIELD TYPE
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

X_FRAME_OPTIONS = 'SAMEORIGIN'


# DJANGO-FILER
# ------------------------------------------------------------------------------
THUMBNAIL_HIGH_RESOLUTION = True

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters'
)


# WAGTAIL
# ------------------------------------------------------------------------------
WAGTAIL_SITE_NAME = 'Digital Meal'
WAGTAILADMIN_BASE_URL = os.getenv('WAGTAILADMIN_BASE_URL', None)

WAGTAILIMAGES_EXTENSIONS = ['gif', 'jpg', 'jpeg', 'png', 'webp', 'svg']


# CKEditor SETTINGS
# ------------------------------------------------------------------------------
# See separate config file.


# E-MAIL SETTINGS
# ------------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = os.environ['EMAIL_PORT']
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
DEFAULT_FROM_EMAIL = os.environ['DEFAULT_FROM_EMAIL']


# DIGITAL MEAL
# ------------------------------------------------------------------------------
DAYS_TO_DONATION_DELETION = 180

# Portability
TIKTOK_AUTH_URL = os.environ.get('TIKTOK_AUTH_URL', 'https://www.tiktok.com/v2/auth/authorize/')
TIKTOK_TOKEN_URL = os.environ.get('TIKTOK_TOKEN_URL', 'https://open.tiktokapis.com/v2/oauth/token/')
TIKTOK_USER_INFO_URL = os.environ.get('TIKTOK_USER_INFO_URL', 'https://open.tiktokapis.com/v2/user/info/')
TIKTOK_CLIENT_KEY = os.environ['TIKTOK_CLIENT_KEY']
TIKTOK_CLIENT_SECRET = os.environ['TIKTOK_CLIENT_SECRET']
TIKTOK_REDIRECT_URL = os.environ['TIKTOK_REDIRECT_URL']


# DDM SETTINGS
# ------------------------------------------------------------------------------
WEBPACK_LOADER = {
    'DDM_UPLOADER': {
        'CACHE': True,
        'BUNDLE_DIR_NAME': 'ddm_core/frontend/uploader/',
        'STATS_FILE': os.path.join(STATIC_ROOT, 'ddm_core/frontend/uploader/webpack-stats.json'),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map']
    },
    'DDM_QUESTIONNAIRE': {
        'CACHE': True,
        'BUNDLE_DIR_NAME': 'ddm_core/frontend/questionnaire/',
        'STATS_FILE': os.path.join(STATIC_ROOT, 'ddm_core/frontend/questionnaire/webpack-stats.json'),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map']
    }
}

DDM_SETTINGS = {
    'EMAIL_PERMISSION_CHECK':  r'.*(\.|@)uzh\.ch$',
}

CKEDITOR_5_FILE_UPLOAD_PERMISSION = 'authenticated'
CKEDITOR_5_ALLOW_ALL_FILE_TYPES = True
CKEDITOR_5_UPLOAD_FILE_TYPES = ['jpeg', 'pdf', 'png', 'mp4']


# WAGTAIL-VIDEOS
# ------------------------------------------------------------------------------
WAGTAIL_VIDEOS_DISABLE_TRANSCODE = True
