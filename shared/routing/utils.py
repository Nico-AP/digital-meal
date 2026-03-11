from django.conf import settings

from shared.routing.constants import MDMRoutingContext, MDMRoutingModes


def get_routing_context(request) -> MDMRoutingContext:
    """Get the routing context for a request."""

    # SUBDOMAIN Mode
    if settings.MDM_ROUTING_MODE == MDMRoutingModes.SUBDOMAIN:
        host = request.get_host().split(":")[0].lower()
        if host == settings.MDM_SUBDOMAIN:
            return MDMRoutingContext.MY_DM
        return MDMRoutingContext.DM_MAIN

    # URL_PREFIX Mode
    prefix = settings.MDM_URL_PREFIX.strip("/")
    path_parts = request.path.strip("/").split("/")

    if path_parts[0] == prefix:
        return MDMRoutingContext.MY_DM
    return MDMRoutingContext.DM_MAIN
