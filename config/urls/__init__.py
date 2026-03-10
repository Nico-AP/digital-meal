"""
URL Configuration
=================

This project supports two routing modes, controlled by ``MDM_ROUTING_MODE``:

URL_PREFIX mode
---------------
MDM views are served under a path prefix (e.g. ``/mdm/``). Standard Django
``reverse()`` works normally for all views. Use this mode for development and
simple deployments.

SUBDOMAIN mode
--------------
MDM views are served on a separate subdomain (e.g. ``mdm.example.com``).
Routing is handled by ``SubdomainRoutingMiddleware``, which assigns
`config.urls.mdm_conf` to requests arriving at ``settings.MDM_SUBDOMAIN``. All
other hosts use ``ROOT_URLCONF`` (`config.urls.main_conf`).

MDM patterns are registered in ``ROOT_URLCONF`` under ``settings.MDM_URL_PREFIX``
even in SUBDOMAIN mode, but are never reachable there — the middleware raises
``Http404`` for any request resolving to the ``mdm`` namespace on the main domain.
The registration exists so that ``absolute_reverse()`` can reverse non-MDM views
from within MDM context without raising ``NoReverseMatch``.

In SUBDOMAIN mode, ``reverse("mdm:some-view")`` returns a prefixed path that
is incorrect for actual use. Always use ``absolute_reverse()`` instead, which
reverses against the correct per-domain urlconf and prepends the appropriate
scheme and host.

    # Can cause issues in SUBDOMAIN mode:
    url = reverse("mdm:dashboard")

    # Always correct:
    url = absolute_reverse("mdm:dashboard")

``absolute_reverse()`` is safe in all routing modes, so prefer it over plain
``reverse()`` for any MDM or cross-domain view throughout the codebase.
"""
