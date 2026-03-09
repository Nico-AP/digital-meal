"""
URL configuration for the MDM subdomain (SUBDOMAIN routing mode only).

SubdomainRoutingMiddleware sets request.urlconf to this module for requests
arriving at settings.MDM_SUBDOMAIN. MDM patterns appear first so they are
matched correctly. Wagtail page-serving is intentionally omitted here; add
wagtail.urls when Wagtail pages need to be served on the MDM subdomain too.
"""

from config.urls.base import base_urlpatterns
from shared.routing.urls import get_mdm_urlpatterns

urlpatterns = get_mdm_urlpatterns() + list(base_urlpatterns)
