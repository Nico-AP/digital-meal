from urllib.parse import urlencode

from django.conf import settings
from django.urls import include, path, reverse
from django.utils.functional import lazy

from shared.routing.constants import _MAIN_URLCONF, _MDM_URLCONF, MDMRoutingModes


def get_mdm_urlpatterns(url_path: str):
    """Called from main urls.py"""
    return [path(url_path, include("mydigitalmeal.core.urls", namespace="mdm"))]


def _select_urlconf(viewname: str) -> str:
    """Pick the correct urlconf for the current routing mode.

    In SUBDOMAIN mode, MDM and main URL configs are separate
    and must be referenced explicitly.
    In URL_PREFIX mode, the root URL config includes both,
    so either view name can be resolved.
    """
    if settings.MDM_ROUTING_MODE == MDMRoutingModes.SUBDOMAIN:
        return _MDM_URLCONF if viewname.startswith("mdm:") else _MAIN_URLCONF
    return settings.ROOT_URLCONF


def _build_absolute_url(path: str, viewname: str) -> str:
    """Prepend scheme + domain to ``path`` in SUBDOMAIN mode.

    The caller is responsible for having already reversed against the
    right urlconf. The trailing-slash normalisation only touches the
    path portion: any pre-existing query string or fragment is split off
    first and re-attached afterwards, so callers passing a path like
    ``/foo?bar=baz`` don't end up with the slash inside the query.
    """
    if settings.MDM_ROUTING_MODE != MDMRoutingModes.SUBDOMAIN:
        return path

    # Keep slash-normalisation away from any query string / fragment.
    suffix_start = min(
        (i for i in (path.find("?"), path.find("#")) if i != -1),
        default=len(path),
    )
    path_only, suffix = path[:suffix_start], path[suffix_start:]
    if not path_only.endswith("/"):
        path_only = path_only + "/"

    scheme = settings.MDM_ROUTING_SCHEME
    domain = (
        settings.MDM_SUBDOMAIN
        if viewname.startswith("mdm:")
        else settings.MDM_MAIN_DOMAIN
    )
    return f"{scheme}://{domain}{path_only}{suffix}"


def absolute_reverse(
    viewname: str,
    *args,
    urlconf: str | None = None,
    query=None,
    **kwargs,
) -> str:
    """Reverse ``viewname`` to a routing-mode-aware URL.

    Positional ``*args`` and keyword ``**kwargs`` are forwarded to
    Django's `django.urls.reverse` as the URL pattern's
    ``args`` / ``kwargs`` respectively (pass one or the other, not both
    — same constraint as Django's ``reverse``).

    Args:
        viewname: Namespaced view name. The ``mdm:`` prefix selects the
            MDM subdomain in SUBDOMAIN mode; anything else goes to the
            main domain.
        *args: Positional URL pattern arguments.
        urlconf: Explicit urlconf override. Auto-selected from the view
            name and routing mode if omitted.
        query: Optional mapping or sequence of ``(key, value)`` pairs to
            be appended as a query string. Encoded with
            `urllib.parse.urlencode` (``doseq=True``).
        **kwargs: Keyword URL pattern arguments.

    Returns:
        In SUBDOMAIN mode an absolute URL (``scheme://domain/path?query``);
        in URL_PREFIX mode a relative URL (``/path?query``).
    """
    if urlconf is None:
        urlconf = _select_urlconf(viewname)

    path = reverse(
        viewname,
        urlconf=urlconf,
        args=args or None,
        kwargs=kwargs or None,
    )
    url = _build_absolute_url(path, viewname)
    if query:
        url = f"{url}?{urlencode(query, doseq=True)}"
    return url


def absolute_reverse_lazy(
    viewname: str,
    *args,
    urlconf: str | None = None,
    query=None,
    **kwargs,
):
    """Lazy variant of ``absolute_reverse``.

    Defers the entire reversal — including urlconf selection — to first
    string coercion, so it's safe to call at import time before
    settings or URLConfs are fully wired.
    """
    return lazy(absolute_reverse, str)(
        viewname,
        *args,
        urlconf=urlconf,
        query=query,
        **kwargs,
    )
