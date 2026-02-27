from .production import *  # noqa: F403
from .production import DATABASES

# Disable SSL redirects for testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_PRELOAD = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_PROXY_SSL_HEADER = None

DATABASES["default"]["OPTIONS"] = {"sslmode": "disable"}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ensure ADMINS is set for email tests
ADMINS = [("Test Admin", "admin@test.com")]

CELERY_TASK_ALWAYS_EAGER = True  # tasks run inline, no worker needed


# Override Settings where needed
SALT_KEY = "ci-mock-salt-123"

SERVER_EMAIL = "ci@test.com"

EMAIL_HOST = "ci.host"
EMAIL_PORT = 587
EMAIL_HOST_USER = "ci_host"
EMAIL_HOST_PASSWORD = "ci_host_pw"  # noqa: S105
DEFAULT_FROM_EMAIL = "ci@test.com"

TIKTOK_CLIENT_KEY = "ci-mock-key"
TIKTOK_CLIENT_SECRET = "ci-mock-secret"  # noqa: S105
TIKTOK_REDIRECT_URL = "https://ci-mock-url.com"
