"""
Routing configuration for multi-context serving.

This module provides the infrastructure to serve the My Digital Meal (MDM)
sub-application either under a dedicated subdomain (e.g. my.site.com)
or a URL prefix (e.g. site.com/my/),
controlled entirely via environment variables with no code changes required.

Configuration:
    MDM_ROUTING_TYPE: "SUBDOMAIN" or "URL_PREFIX"
    MDM_SUBDOMAIN:    the subdomain to match in SUBDOMAIN mode, e.g. "my.site.com"
    MDM_URL_PREFIX:   the URL prefix to use in URL_PREFIX mode, e.g. "my/"
    MAIN_DOMAIN:      the main site domain, e.g. "site.com"

Components:
    middleware: Blocks MDM URLs from being accessed on the wrong domain
        in SUBDOMAIN mode.
    urls: URL pattern registration and absolute URL helpers
        (absolute_reverse, absolute_reverse_lazy).
        Import these instead of django.urls.reverse to ensure correct domain-aware
        URL generation.
    templatetags/routing_tags: Custom {% absolute_url %} template tag that wraps the
        above absolute_reverse() helper.
    allauth_integration: Authentication context management for the two routing
    contexts (MY_DM and DM_EDUCATION), including session handling,
    loading templates context-dependent, and automatic logout on context switches.
"""
