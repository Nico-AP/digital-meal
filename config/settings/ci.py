from .production import *  # noqa: F403
from .production import DATABASES

DEBUG = False

ALLOWED_HOSTS = ["domain.com", "my.domain.com", "127.0.0.1", "localhost"]

# ROUTING SETUP
MDM_ROUTING_TYPE = "SUBDOMAIN"
MDM_ROUTING_SCHEME = "http"
MDM_MAIN_DOMAIN = "domain.com"
MDM_SUBDOMAIN = "my.domain.com"
MDM_URL_PREFIX = "my/"

# Disable SSL redirects for testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_PRELOAD = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_PROXY_SSL_HEADER = None

ALLAUTH_TRUSTED_CLIENT_IP_HEADER = None
ACCOUNT_RATE_LIMITS = {}  # disable all rate limits in CI

DATABASES["default"]["OPTIONS"] = {"init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ensure ADMINS is set for email tests
ADMINS = [("Test Admin", "admin@test.com")]

CELERY_TASK_ALWAYS_EAGER = True  # tasks run inline, no worker needed
