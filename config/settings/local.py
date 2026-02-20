from pathlib import Path

import ddm.core

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE, env

ALLOWED_HOSTS = env.str("ALLOWED_HOSTS").split()

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = True

SITE_ID = 1

# django-debug-toolbar - https://github.com/django-commons/django-debug-toolbar
# ------------------------------------------------------------------------------
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    DEBUG_TOOLBAR_CONFIG = {
        "DISABLE_PANELS": [
            "debug_toolbar.panels.redirects.RedirectsPanel",
            # Disable profiling panel due to an issue with Python 3.12:
            # https://github.com/jazzband/django-debug-toolbar/issues/1875
            "debug_toolbar.panels.profiling.ProfilingPanel",
        ],
        "SHOW_TEMPLATE_CONTEXT": True,
    }
    INTERNAL_IPS = ["127.0.0.1"]


# DATABASE
# ------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "dm.sqlite",
    }
}


# E-MAIL SETTINGS
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# CELERY
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True  # tasks run inline, no worker needed


# DDM SETTINGS
# ------------------------------------------------------------------------------
WEBPACK_LOADER = {
    "DDM_UPLOADER": {
        "CACHE": True,
        "BUNDLE_DIR_NAME": "ddm_core/frontend/uploader/",
        "STATS_FILE": Path(ddm.core.__file__).parent
        / "static/ddm_core/frontend/uploader/webpack-stats.json",
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update.js", r".+\.map"],
    },
    "DDM_QUESTIONNAIRE": {
        "CACHE": True,
        "BUNDLE_DIR_NAME": "ddm_core/frontend/questionnaire/",
        "STATS_FILE": Path(ddm.core.__file__).parent
        / "static/ddm_core/frontend/questionnaire/webpack-stats.json",
        "POLL_INTERVAL": 0.1,
        "TIMEOUT": None,
        "IGNORE": [r".+\.hot-update.js", r".+\.map"],
    },
}

DDM_SETTINGS = {
    "EMAIL_PERMISSION_CHECK": r".*(\.|@).*\.ch$",
}
