"""
URL configuration for the main domain in SUBDOMAIN routing mode.

SubdomainRoutingMiddleware sets request.urlconf to this module for requests
arriving at settings.MAIN_DOMAIN. Wagtail pages are served normally. MDM
patterns are appended last so that Wagtail's catch-all intercepts them for
request matching (MDM views are unreachable here), while reverse() can still
find them by name for use with absolute_reverse().
"""

from django.urls import include, path

from config.urls.base import base_urlpatterns
from config.urls.ddm_integration import ddm_auth_stubs
from shared.routing.urls import get_mdm_urlpatterns

urlpatterns = [
    *base_urlpatterns,
    path("", include("digital_meal.core.urls")),
    *get_mdm_urlpatterns(),
    *ddm_auth_stubs,
    path("cms/", include("wagtail.admin.urls")),
    path("documents/", include("wagtail.documents.urls")),
    path("", include("wagtail.urls")),
]
