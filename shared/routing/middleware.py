from django.conf import settings
from django.http import Http404
from django.urls import Resolver404, resolve

from shared.routing.constants import MDMRoutingTypes


class SubdomainRoutingMiddleware:
    """Blocks URLs from being accessed on the wrong domain in SUBDOMAIN mode."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.MDM_ROUTING_TYPE == MDMRoutingTypes.SUBDOMAIN:
            host = request.get_host().split(":")[0].lower()
            is_mdm_host = host == settings.MDM_SUBDOMAIN

            try:
                match = resolve(request.path_info)
                if "mdm" in match.namespaces and not is_mdm_host:
                    raise Http404

                if "mdm" not in match.namespaces and is_mdm_host:
                    raise Http404
            except Resolver404:
                pass  # let Django handle unmatched URLs normally

        return self.get_response(request)
