from django.conf import settings

from shared.portability.constants import PortabilityContexts
from shared.routing.constants import MDMRoutingModes


def get_request_context(request) -> str:
    # SUBDOMAIN Mode
    if settings.MDM_ROUTING_MODE == MDMRoutingModes.SUBDOMAIN:
        host = request.get_host().split(":")[0].lower()
        if host == settings.MDM_SUBDOMAIN:
            return PortabilityContexts.MY_DM
        return PortabilityContexts.DM_EDU

    # URL_PREFIX Mode
    prefix = settings.MDM_URL_PREFIX.strip("/")
    path_parts = request.path.strip("/").split("/")

    if path_parts[0] == prefix:
        return PortabilityContexts.MY_DM
    return PortabilityContexts.DM_EDU
