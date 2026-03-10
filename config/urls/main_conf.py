"""
Root URL configuration (ROOT_URLCONF) and main-domain urlconf (_MAIN_URLCONF).

In URL_PREFIX mode, this module serves all views and is used directly by
absolute_reverse() for URL reversal.

In SUBDOMAIN mode, SubdomainRoutingMiddleware assigns `config.urls.mdm_conf`
to requests arriving at settings.MDM_SUBDOMAIN. All other hosts (including
settings.MDM_MAIN_DOMAIN and 'testserver' in tests) use this module.

MDM patterns are registered here under settings.MDM_URL_PREFIX even in
SUBDOMAIN mode. They are never reachable on the main domain — the middleware
raises Http404 for any request that resolves to the 'mdm' namespace. The
prefix registration exists solely so that absolute_reverse() can reverse
non-MDM views from within MDM context without raising NoReverseMatch.

Never use plain reverse() for MDM views. Use absolute_reverse() instead,
which routes reversal to the correct per-domain urlconf.
"""

from django.conf import settings
from django.urls import include, path

from config.urls.base import base_urlpatterns
from config.urls.ddm_integration import ddm_auth_stubs
from shared.routing.urls import get_mdm_urlpatterns

urlpatterns = [
    *base_urlpatterns,
    path("", include("digital_meal.core.urls")),
    *get_mdm_urlpatterns(settings.MDM_URL_PREFIX),  # always includes a prefix here
    *ddm_auth_stubs,
    path("cms/", include("wagtail.admin.urls")),
    path("documents/", include("wagtail.documents.urls")),
    path("", include("wagtail.urls")),
]
