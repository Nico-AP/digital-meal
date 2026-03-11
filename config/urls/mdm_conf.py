"""
URL configuration for the MDM subdomain (SUBDOMAIN routing mode only).

SubdomainRoutingMiddleware assigns this module as request.urlconf for requests
arriving at settings.MDM_SUBDOMAIN. It is never used in URL_PREFIX mode.

MDM patterns are registered without a path prefix here — the subdomain itself
provides the domain separation, so no prefix is needed. In URL_PREFIX mode,
the prefix is applied in ROOT_URLCONF instead.

Wagtail page-serving is intentionally omitted. Add wagtail.urls here if
Wagtail pages need to be served on the MDM subdomain.
"""

from django.conf import settings

from config.urls.base import base_urlpatterns
from shared.routing.constants import MDMRoutingModes
from shared.routing.urls import get_mdm_urlpatterns

if settings.MDM_ROUTING_MODE == MDMRoutingModes.URL_PREFIX:
    mdm_prefix = settings.MDM_URL_PREFIX
else:
    mdm_prefix = ""

urlpatterns = list(base_urlpatterns) + get_mdm_urlpatterns(mdm_prefix)

handler400 = "shared.views.custom_400"
handler403 = "shared.views.custom_403"
handler404 = "shared.views.custom_404"
handler500 = "shared.views.custom_500"
