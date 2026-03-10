from django.conf import settings
from django.http import Http404
from django.urls import Resolver404, resolve

from shared.routing.constants import _MAIN_URLCONF, _MDM_URLCONF, MDMRoutingModes


class SubdomainRoutingMiddleware:
    """
    In SUBDOMAIN mode, routes each domain to a dedicated URL conf.

    - Requests on settings.MDM_SUBDOMAIN use config.urls_mdm: MDM views are
      served, Wagtail pages are not (add wagtail.urls there when needed).
    - Requests on settings.MDM_MAIN_DOMAIN use config.urls_main: Wagtail pages
      are served, MDM views are unreachable (Wagtail catch-all intercepts them).
    - All other hosts (e.g. testserver in tests) keep the default URL conf
      (config.urls), where MDM patterns appear before Wagtail so that tests
      and reverse() work without requiring a specific host header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.MDM_ROUTING_MODE == MDMRoutingModes.SUBDOMAIN:
            host = request.get_host().split(":")[0].lower()
            if host == settings.MDM_SUBDOMAIN:
                request.urlconf = _MDM_URLCONF
            elif host == settings.MDM_MAIN_DOMAIN:
                request.urlconf = _MAIN_URLCONF

                try:
                    match = resolve(request.path_info)
                    if "mdm" in match.namespaces:
                        raise Http404

                except Resolver404:
                    pass  # let Django handle unmatched URLs normally

        return self.get_response(request)
