from django.http import Http404
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from shared.routing.constants import MDMRoutingTypes
from shared.routing.middleware import SubdomainRoutingMiddleware


@override_settings(ALLOWED_HOSTS=["my.dm.com", "dm.com"])
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
        middleware(request)  # should not raise

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
    )
    def test_mdm_url_on_wrong_host_raises_404(self):
        """MDM URL accessed from main domain is blocked."""
        url = reverse("mdm:userflow:landing_page")
        request = self.factory.get(url, HTTP_HOST="dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        with self.assertRaises(Http404):
            middleware(request)

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
    )
    def test_mdm_url_on_correct_host_does_not_raise(self):
        """MDM URL accessed from MDM subdomain passes through."""
        url = reverse("mdm:userflow:landing_page")
        request = self.factory.get(url, HTTP_HOST="my.dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)  # should not raise

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
    )
    def test_host_with_port_is_handled(self):
        """Port number is stripped before host comparison."""
        url = reverse("mdm:userflow:landing_page")
        request = self.factory.get(url, HTTP_HOST="my.dm.com:8000")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)  # should not raise

    @override_settings(
        MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
    )
    def test_non_mdm_url_on_main_domain_is_not_blocked(self):
        """Non-MDM URLs on the main domain are never blocked by this middleware."""
        url = reverse("newsletter")
        request = self.factory.get(url, HTTP_HOST="dm.com")
        middleware = SubdomainRoutingMiddleware(self.get_response)
        middleware(request)  # should not raise


@override_settings(
    ROOT_URLCONF="config.urls",
    MDM_ROUTING_TYPE=MDMRoutingTypes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
)
class URLModeIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_mdm_prefix_resolves(self):
        url = reverse("mdm:userflow:landing_page")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unknown_path_returns_404(self):
        response = self.client.get("/other/")
        self.assertEqual(response.status_code, 404)


@override_settings(
    ROOT_URLCONF="config.urls",
    MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    ALLOWED_HOSTS=["my.dm.com", "dm.com"],
)
class SubdomainModeIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_mdm_view_reachable_from_mdm_subdomain(self):
        url = reverse("mdm:userflow:landing_page")
        response = self.client.get(url, headers={"host": "my.dm.com"})
        self.assertEqual(response.status_code, 200)

    def test_mdm_view_blocked_from_main_domain(self):
        url = reverse("mdm:userflow:landing_page")
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
