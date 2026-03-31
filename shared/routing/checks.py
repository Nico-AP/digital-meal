from django.conf import settings
from django.core.checks import Error, register

from shared.routing.constants import MDMRoutingModes


@register()
def check_subdomain_session_cookie_config(app_configs, **kwargs):
    """Warn when SESSION_COOKIE_DOMAIN is not set in SUBDOMAIN routing mode.

    In SUBDOMAIN mode the TikTok portability callback URL lives on the main
    domain while the auth flow is initiated from the MDM subdomain. Without a
    shared session cookie domain the callback receives an empty session and
    the state token comparison always fails.
    """
    errors = []
    if getattr(settings, "MDM_ROUTING_MODE", None) == MDMRoutingModes.SUBDOMAIN:
        if not getattr(settings, "SESSION_COOKIE_DOMAIN", None):
            errors.append(
                Error(
                    "SESSION_COOKIE_DOMAIN must be set when MDM_ROUTING_MODE "
                    "is 'SUBDOMAIN'.",
                    hint=(
                        "Set SESSION_COOKIE_DOMAIN to '.yourdomain.com' (note the "
                        "leading dot) so that the session cookie is shared across "
                        "subdomains. Without this the TikTok portability OAuth "
                        "callback will fail because the session created on the MDM "
                        "subdomain is not sent to the main domain callback URL."
                    ),
                    id="routing.E001",
                )
            )
    return errors
