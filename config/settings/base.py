import json
import socket
from pathlib import Path

from environs import Env

env = Env()
env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# APPLICATION DEFINITIONS
# ------------------------------------------------------------------------------
SECRET_KEY = env.str("DJANGO_SECRET")
SALT_KEY = env.str("SALT_KEY")

ALLOWED_HOSTS = env.str("ALLOWED_HOSTS", default="localhost 127.0.0.1").split()

ADMINS = [tuple(admin) for admin in json.loads(env.str("ADMINS", "[]"))]

SERVER_EMAIL = env.str("DEFAULT_FROM_EMAIL")

DJANGO_CORE = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
]

DJANGO_THIRD_PARTY = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_htmx",
]

DIGITAL_MEAL_EDUCATION_APPS = [
    "digital_meal.core",
    "digital_meal.tool",
    "digital_meal.website",
    "digital_meal.reports",
    "digital_meal.dashboard",
    "qr_code",
]

MY_DIGITAL_MEAL_APPS = [
    "mydigitalmeal",
    "mydigitalmeal.core",
    "mydigitalmeal.reports",
    "mydigitalmeal.statistics",
    "mydigitalmeal.userflow",
    "mydigitalmeal.datadonation",
    "mydigitalmeal.profiles",
    "mydigitalmeal.questionnaire",
    "mydigitalmeal.infopages",
]

SHARED_APPS = [
    "shared.portability",
]

DDM_APPS = [
    "ddm",
    "ddm.auth",
    "ddm.logging",
    "ddm.questionnaire",
    "ddm.datadonation",
    "ddm.participation",
    "ddm.projects",
    "ddm.core",
    "webpack_loader",
    "rest_framework",
    "rest_framework.authtoken",
    "django_ckeditor_5",
]

WAGTAIL_APPS = [
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.locales",
    "wagtail.contrib.simple_translation",
    "wagtail",
    "wagtailvideos",
    # "wagtail_modeladmin",  TODO: Remove properly
    "taggit",
]

INSTALLED_APPS = (
    DJANGO_CORE
    + DJANGO_THIRD_PARTY
    + WAGTAIL_APPS
    + DDM_APPS
    + DIGITAL_MEAL_EDUCATION_APPS
    + MY_DIGITAL_MEAL_APPS
    + SHARED_APPS
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "shared.allauth_integration.middleware.SubdomainMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "digital_meal.website.middleware.RestrictDDMMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            "digital_meal/templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "ddm.core.context_processors.add_ddm_version",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# INTERNATIONALIZATION
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Zurich"
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    Path(BASE_DIR) / "locale",
]

WAGTAILSIMPLETRANSLATION_SYNC_PAGE_TREE = True

WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [("de", "Deutsch")]


# USER AUTHENTICATION AND PASSWORD VALIDATION
# ------------------------------------------------------------------------------
AUTH_USER_MODEL = "tool.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_REDIRECT_URL = "/tool/"
LOGOUT_REDIRECT_URL = "/"


# DANGO-ALLAUTH
# ------------------------------------------------------------------------------
ACCOUNT_ADAPTER = "shared.allauth_integration.adapters.SubdomainAccountAdapter"
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "email2*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

ACCOUNT_LOGOUT_REDIRECT_URL = "/"

ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_MAX_EMAIL_ADDRESSES = 2
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "Digital Meal | "

ACCOUNT_FORMS = {"signup": "digital_meal.tool.forms.SimpleSignupForm"}

ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_SIGNUP_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = (
    5 * 60
)  # Time in seconds until code expires after sending.
ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS = 5

# Setting overrides for My Digital Meal
ALLAUTH_MDM = {
    "ACCOUNT_SIGNUP_FIELDS": ["email*"],  # has no effect, here for reference
    "ACCOUNT_EMAIL_VERIFICATION": "none",
    "ACCOUNT_EMAIL_SUBJECT_PREFIX": "My Digital Meal | ",
    "ACCOUNT_SIGNUP_BY_CODE_ENABLED": True,
    "ACCOUNT_LOGOUT_REDIRECT_URL": "/my/",
}

# STATIC FILES
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = Path(BASE_DIR) / "staticfiles/"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(BASE_DIR) / "media/"


# DEFAULT PRIMARY KEY FIELD TYPE
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

X_FRAME_OPTIONS = "SAMEORIGIN"


# DJANGO-FILER
# ------------------------------------------------------------------------------
THUMBNAIL_HIGH_RESOLUTION = True

THUMBNAIL_PROCESSORS = (
    "easy_thumbnails.processors.colorspace",
    "easy_thumbnails.processors.autocrop",
    "filer.thumbnail_processors.scale_and_crop_with_subject_location",
    "easy_thumbnails.processors.filters",
)


# WAGTAIL
# ------------------------------------------------------------------------------
WAGTAIL_SITE_NAME = "Digital Meal"
WAGTAILADMIN_BASE_URL = env.str("WAGTAILADMIN_BASE_URL", None)

WAGTAILIMAGES_EXTENSIONS = ["gif", "jpg", "jpeg", "png", "webp", "svg"]


# CKEditor SETTINGS
# ------------------------------------------------------------------------------
# See separate config file.


# E-MAIL SETTINGS
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = True
EMAIL_HOST = env.str("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")


# CELERY
# ------------------------------------------------------------------------------
REDIS_URL = env.str("REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_SSL = REDIS_URL.startswith("rediss://")

if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
CELERY_RESULT_BACKEND_MAX_RETRIES = 10

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_TIME_LIMIT = 10 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60
CELERY_TASK_SEND_SENT_EVENT = True

CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_keepalive": True,
    "socket_keepalive_options": {
        socket.TCP_KEEPIDLE: 60,
        socket.TCP_KEEPINTVL: 10,
        socket.TCP_KEEPCNT: 5,
    },
}

# DIGITAL MEAL
# ------------------------------------------------------------------------------
DAYS_TO_DONATION_DELETION = 180
ALLOWED_REPORT_DOMAINS = env.str("ALLOWED_REPORT_DOMAINS", "").split()

# Portability
TIKTOK_AUTH_URL = env.str(
    "TIKTOK_AUTH_URL", "https://www.tiktok.com/v2/auth/authorize/"
)
TIKTOK_TOKEN_URL = env.str(
    "TIKTOK_TOKEN_URL", "https://open.tiktokapis.com/v2/oauth/token/"
)
TIKTOK_USER_INFO_URL = env.str(
    "TIKTOK_USER_INFO_URL", "https://open.tiktokapis.com/v2/user/info/"
)
TIKTOK_CLIENT_KEY = env.str("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = env.str("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URL = env.str("TIKTOK_REDIRECT_URL")


# DDM SETTINGS
# ------------------------------------------------------------------------------
WEBPACK_LOADER = {
    "DDM_UPLOADER": {
        "CACHE": True,
        "BUNDLE_DIR_NAME": "ddm_core/frontend/uploader/",
        "STATS_FILE": Path(STATIC_ROOT)
        / "ddm_core/frontend/uploader/webpack-stats.json",
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update.js", r".+\.map"],
    },
    "DDM_QUESTIONNAIRE": {
        "CACHE": True,
        "BUNDLE_DIR_NAME": "ddm_core/frontend/questionnaire/",
        "STATS_FILE": Path(STATIC_ROOT)
        / "ddm_core/frontend/questionnaire/webpack-stats.json",
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update.js", r".+\.map"],
    },
}

DDM_SETTINGS = {
    "EMAIL_PERMISSION_CHECK": r".*(\.|@)uzh\.ch$",
}

CKEDITOR_5_FILE_UPLOAD_PERMISSION = "authenticated"
CKEDITOR_5_ALLOW_ALL_FILE_TYPES = True
CKEDITOR_5_UPLOAD_FILE_TYPES = ["jpeg", "pdf", "png", "mp4"]


# WAGTAIL-VIDEOS
# ------------------------------------------------------------------------------
WAGTAIL_VIDEOS_DISABLE_TRANSCODE = True


# LOGGING
# ------------------------------------------------------------------------------
LOG_DIR = Path(BASE_DIR) / "logs"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
        "json": {
            "()": "digital_meal.core.logging_utils.JsonFormatter",
        },
    },
    "filters": {
        "require_debug_false": {"class": "django.utils.log.RequireDebugFalse"},
        "throttle_admin_email": {
            "()": "config.logging_utils.ThrottledAdminEmailFilter",
            "throttle_seconds": 180,
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOG_DIR) / "django.log",
            "maxBytes": 1024 * 1024 * 15,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "portability_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOG_DIR) / "portability.log",
            "maxBytes": 1024 * 1024 * 15,
            "backupCount": 5,
            "formatter": "json",
        },
        "mdm_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(BASE_DIR) / "logs" / "mydigitalmeal.log",
            "maxBytes": 1024 * 1024 * 15,
            "backupCount": 5,
            "formatter": "json",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOG_DIR) / "errors.log",
            "maxBytes": 1024 * 1024 * 15,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "security_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Path(LOG_DIR) / "security.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": False,
            "filters": ["require_debug_false", "throttle_admin_email"],
        },
    },
    "loggers": {
        "": {
            "handlers": ["file", "error_file", "console", "mail_admins"],
            "level": "WARNING",
        },
        "django": {
            "handlers": ["file", "error_file", "mail_admins", "console"],
            "propagate": False,
            "level": "WARNING",
        },
        "django.server": {
            "handlers": ["console"],
            "propagate": False,
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["error_file", "mail_admins", "console"],
            "propagate": False,
            "level": "ERROR",
        },
        "django.security": {
            "handlers": ["security_file", "mail_admins", "console"],
            "propagate": False,
            "level": "WARNING",
        },
        "digital_meal": {
            "handlers": ["file", "error_file", "mail_admins", "console"],
            "propagate": False,
            "level": "INFO",
        },
        "shared.portability": {
            "handlers": ["portability_file", "error_file", "mail_admins", "console"],
            "propagate": False,
            "level": "INFO",
        },
        "mydigitalmeal": {
            "handlers": ["mdm_file", "error_file", "console"],
            "propagate": False,
            "level": "INFO",
        },
    },
}
