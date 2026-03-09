from django.conf import settings
from django.urls import include, path, reverse, reverse_lazy
from django.utils.functional import lazy

from shared.routing.constants import MDMRoutingTypes


def get_mdm_urlpatterns():
    """Called from main urls.py"""
    if settings.MDM_ROUTING_TYPE == MDMRoutingTypes.URL_PREFIX:
        return [
            path(
                settings.MDM_URL_PREFIX,
                include("mydigitalmeal.core.urls", namespace="mdm"),
            )
        ]
    return [path("", include("mydigitalmeal.core.urls", namespace="mdm"))]


def _build_absolute_url(path: str, viewname: str) -> str:
    """Apply domain prefix in SUBDOMAIN mode."""
    if settings.MDM_ROUTING_TYPE != MDMRoutingTypes.SUBDOMAIN:
        return path

    scheme = settings.MDM_ROUTING_SCHEME

    if (
        viewname.startswith("mdm:")
        and settings.MDM_ROUTING_TYPE == MDMRoutingTypes.SUBDOMAIN
    ):
        domain = settings.MDM_SUBDOMAIN
    else:
        domain = settings.MDM_MAIN_DOMAIN

    return f"{scheme}://{domain}{path}"


def absolute_reverse(viewname, urlconf=None, *args, **kwargs):
    # Always use the root URL conf so that cross-domain reversals work
    # regardless of which per-domain URL conf is active on the current request.
    if not urlconf:
        urlconf = settings.ROOT_URLCONF

    path = reverse(viewname, *args, urlconf=urlconf, **kwargs)
    return _build_absolute_url(path, viewname)


def absolute_reverse_lazy(viewname, urlconf=None, *args, **kwargs):
    if not urlconf:
        urlconf = settings.ROOT_URLCONF

    return lazy(_build_absolute_url, str)(
        reverse_lazy(viewname, *args, urlconf=urlconf, **kwargs),
        viewname,
    )
