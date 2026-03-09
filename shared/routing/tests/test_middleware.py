from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from shared.routing.constants import MDMRoutingTypes
from shared.routing.middleware import (
    _MAIN_URLCONF,
    _MDM_URLCONF,
    SubdomainRoutingMiddleware,
)


@override_settings(ALLOWED_HOSTS=["my.dm.com", "dm.com", "other.dm.com"])
class SubdomainRoutingMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = lambda request: None  # dummy response

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.URL_PREFIX,
        MDM_URL_PREFIX="my/",
    )
    def test_url_mode_middleware_is_noop(self):
        """In URL_PREFIX mode, middleware does nothing regardless of host."""
        request = self.factory.get("/my/", HTTP_HOST="dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)
        self.assertFalse(hasattr(request, "urlconf"))

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
        MDM_MAIN_DOMAIN="dm.com",
    )
    def test_main_domain_gets_main_urlconf(self):
        """Requests on the main domain use the main URL conf."""
        url = reverse("newsletter")
        request = self.factory.get(url, HTTP_HOST="dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)
        self.assertEqual(request.urlconf, _MAIN_URLCONF)

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
        MDM_MAIN_DOMAIN="dm.com",
    )
    def test_mdm_subdomain_gets_mdm_urlconf(self):
        """Requests on the MDM subdomain use the MDM URL conf."""
        url = reverse("mdm:infopages:background")
        request = self.factory.get(url, HTTP_HOST="my.dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)
        self.assertEqual(request.urlconf, _MDM_URLCONF)

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
        MDM_MAIN_DOMAIN="dm.com",
    )
    def test_host_with_port_is_handled(self):
        """Port number is stripped before host comparison."""
        url = reverse("mdm:infopages:background")
        request = self.factory.get(url, HTTP_HOST="my.dm.com:8000")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)
        self.assertEqual(request.urlconf, _MDM_URLCONF)

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
        MDM_MAIN_DOMAIN="dm.com",
    )
    def test_unknown_host_keeps_default_urlconf(self):
        """Hosts that are neither the MDM subdomain nor the main domain are
        unaffected.
        """
        url = reverse("newsletter")
        request = self.factory.get(url, HTTP_HOST="other.dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)
        self.assertFalse(hasattr(request, "urlconf"))


@override_settings(
    ROOT_URLCONF="config.urls.main_conf",
    MDM_ROUTING_TYPE=MDMRoutingTypes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
)
class URLModeIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_mdm_prefix_resolves(self):
        url = reverse("mdm:infopages:background")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unknown_path_returns_404(self):
        response = self.client.get("/other/")
        self.assertEqual(response.status_code, 404)


@override_settings(
    ROOT_URLCONF="config.urls.main_conf",
    MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
    ALLOWED_HOSTS=["my.dm.com", "dm.com"],
)
class SubdomainModeIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_mdm_view_reachable_from_mdm_subdomain(self):
        # Resolve with the MDM subdomain URL conf so the path matches its
        # root-based patterns.
        url = reverse("mdm:infopages:background", urlconf="config.urls.mdm_conf")
        response = self.client.get(url, headers={"host": "my.dm.com"})
        self.assertEqual(response.status_code, 200)

    def test_mdm_view_blocked_from_main_domain(self):
        # Same path as above; on the main domain Wagtail (catch-all) intercepts
        # it → 404.
        url = reverse("mdm:infopages:background", urlconf="config.urls.main_conf")
        response = self.client.get(url, headers={"host": "dm.com"})
        self.assertEqual(response.status_code, 404)

    def test_non_mdm_view_reachable_from_main_domain(self):
        url = reverse("newsletter")
        response = self.client.get(url, headers={"host": "dm.com"})
        self.assertEqual(response.status_code, 200)

    def test_non_mdm_view_not_reachable_from_mdm_subdomain(self):
        url = reverse("newsletter")
        response = self.client.get(url, headers={"host": "my.dm.com"})
        self.assertEqual(response.status_code, 404)
