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

    scheme = "http" if settings.DEBUG else "https"

    if isinstance(viewname, str) and viewname.startswith("mdm:"):
        return f"{scheme}://{settings.MDM_SUBDOMAIN}{path}"

    return f"{scheme}://{settings.MAIN_DOMAIN}{path}"


def absolute_reverse(viewname, *args, **kwargs):
    path = reverse(viewname, *args, **kwargs)
    return _build_absolute_url(path, viewname)


def absolute_reverse_lazy(viewname, *args, **kwargs):
    return lazy(_build_absolute_url, str)(
        reverse_lazy(viewname, *args, **kwargs),
        viewname,
    )
