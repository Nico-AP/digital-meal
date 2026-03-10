from django.test import RequestFactory, TestCase, override_settings

from shared.portability.constants import PortabilityContexts
from shared.portability.utils import get_request_context
from shared.routing.constants import MDMRoutingModes


@override_settings(ALLOWED_HOSTS=["my.dm.com", "dm.com"])
class UtilsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(
        MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
        MDM_MAIN_DOMAIN="dm.com",
    )
    def test_subdomain_routing_mdm(self):
        request = self.factory.get("/", HTTP_HOST="my.dm.com")
        result = get_request_context(request)
        self.assertEqual(result, PortabilityContexts.MY_DM)

    @override_settings(
        MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.dm.com",
        MDM_MAIN_DOMAIN="dm.com",
    )
    def test_subdomain_routing_dm(self):
        request = self.factory.get("/", HTTP_HOST="dm.com")
        result = get_request_context(request)
        self.assertEqual(result, PortabilityContexts.DM_EDU)

    @override_settings(
        MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX,
        MDM_URL_PREFIX="my/",
    )
    def test_urlprefix_routing_mdm(self):
        request = self.factory.get("/my/")
        result = get_request_context(request)
        self.assertEqual(result, PortabilityContexts.MY_DM)

    @override_settings(
        MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX,
        MDM_URL_PREFIX="my/",
    )
    def test_urlprefix_routing_dm(self):
        request = self.factory.get("/")
        result = get_request_context(request)
        self.assertEqual(result, PortabilityContexts.DM_EDU)
