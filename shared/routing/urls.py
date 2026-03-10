from django.conf import settings
from django.urls import include, path, reverse, reverse_lazy
from django.utils.functional import lazy

from shared.routing.constants import _MAIN_URLCONF, _MDM_URLCONF, MDMRoutingModes


def get_mdm_urlpatterns(url_path: str):
    """Called from main urls.py"""
    return [path(url_path, include("mydigitalmeal.core.urls", namespace="mdm"))]


def _build_absolute_url(path: str, viewname: str) -> str:
    """Apply domain prefix in SUBDOMAIN mode."""
    if settings.MDM_ROUTING_MODE != MDMRoutingModes.SUBDOMAIN:
        return path

    scheme = settings.MDM_ROUTING_SCHEME

    if viewname.startswith("mdm:"):
        # Re-reverse against the MDM urlconf to get the correct path
        path = reverse(viewname, urlconf=_MDM_URLCONF)
        if not path.endswith("/"):
            path = path + "/"
        return f"{scheme}://{settings.MDM_SUBDOMAIN}{path}"

    path = reverse(viewname, urlconf=_MAIN_URLCONF)
    if not path.endswith("/"):
        path = path + "/"
    return f"{scheme}://{settings.MDM_MAIN_DOMAIN}{path}"


def absolute_reverse(viewname, urlconf=None, *args, **kwargs):
    if settings.MDM_ROUTING_MODE == MDMRoutingModes.SUBDOMAIN:
        urlconf = _MDM_URLCONF if viewname.startswith("mdm:") else _MAIN_URLCONF
    else:
        urlconf = settings.ROOT_URLCONF

    path = reverse(viewname, *args, urlconf=urlconf, **kwargs)
    return _build_absolute_url(path, viewname)


def absolute_reverse_lazy(viewname, urlconf=None, *args, **kwargs):
    if settings.MDM_ROUTING_MODE == MDMRoutingModes.SUBDOMAIN:
        urlconf = _MDM_URLCONF if viewname.startswith("mdm:") else _MAIN_URLCONF
    else:
        urlconf = settings.ROOT_URLCONF

    return lazy(_build_absolute_url, str)(
        reverse_lazy(viewname, *args, urlconf=urlconf, **kwargs),
        viewname,
    )
