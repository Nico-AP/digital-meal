from django.test import RequestFactory, TestCase, override_settings

from shared.routing.constants import MDMRoutingModes
from shared.views import (
    custom_400,
    custom_403,
    custom_404,
    custom_500,
    get_template_prefix,
)


@override_settings(
    ALLOWED_HOSTS=["my.dm.com", "dm.com"],
    MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ErrorViewsSubdomainRoutingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.dm_request = self.factory.get("/", HTTP_HOST="dm.com")
        self.mdm_request = self.factory.get("/", HTTP_HOST="my.dm.com")

    def test_dm_main_get_template_prefix(self):
        result = get_template_prefix(self.dm_request)
        self.assertEqual(result, "digital_meal")

    def test_dm_main_custom_400_view(self):
        response_400 = custom_400(self.dm_request, Exception())
        self.assertEqual(response_400.status_code, 400)

    def test_dm_main_custom_403_view(self):
        response_403 = custom_403(self.dm_request, Exception())
        self.assertEqual(response_403.status_code, 403)

    def test_dm_main_custom_404_view(self):
        response_404 = custom_404(self.dm_request, Exception())
        self.assertEqual(response_404.status_code, 404)

    def test_dm_main_custom_500_view(self):
        response_500 = custom_500(self.dm_request)
        self.assertEqual(response_500.status_code, 500)

    def test_mdm_main_get_template_prefix(self):
        result = get_template_prefix(self.mdm_request)
        self.assertEqual(result, "mydigitalmeal")

    def test_mdm_main_custom_400_view(self):
        response_400 = custom_400(self.mdm_request, Exception())
        self.assertEqual(response_400.status_code, 400)

    def test_mdm_main_custom_403_view(self):
        response_403 = custom_403(self.mdm_request, Exception())
        self.assertEqual(response_403.status_code, 403)

    def test_mdm_main_custom_404_view(self):
        response_404 = custom_404(self.mdm_request, Exception())
        self.assertEqual(response_404.status_code, 404)

    def test_mdm_main_custom_500_view(self):
        response_500 = custom_500(self.mdm_request)
        self.assertEqual(response_500.status_code, 500)


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
)
class ErrorViewsUrlPrefixRoutingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.dm_request = self.factory.get("/")
        self.mdm_request = self.factory.get("/my/")

    def test_dm_main_get_template_prefix(self):
        result = get_template_prefix(self.dm_request)
        self.assertEqual(result, "digital_meal")

    def test_dm_main_custom_400_view(self):
        response_400 = custom_400(self.dm_request, Exception())
        self.assertEqual(response_400.status_code, 400)

    def test_dm_main_custom_403_view(self):
        response_403 = custom_403(self.dm_request, Exception())
        self.assertEqual(response_403.status_code, 403)

    def test_dm_main_custom_404_view(self):
        response_404 = custom_404(self.dm_request, Exception())
        self.assertEqual(response_404.status_code, 404)

    def test_dm_main_custom_500_view(self):
        response_500 = custom_500(self.dm_request)
        self.assertEqual(response_500.status_code, 500)

    def test_mdm_main_get_template_prefix(self):
        result = get_template_prefix(self.mdm_request)
        self.assertEqual(result, "mydigitalmeal")

    def test_mdm_main_custom_400_view(self):
        response_400 = custom_400(self.mdm_request, Exception())
        self.assertEqual(response_400.status_code, 400)

    def test_mdm_main_custom_403_view(self):
        response_403 = custom_403(self.mdm_request, Exception())
        self.assertEqual(response_403.status_code, 403)

    def test_mdm_main_custom_404_view(self):
        response_404 = custom_404(self.mdm_request, Exception())
        self.assertEqual(response_404.status_code, 404)

    def test_mdm_main_custom_500_view(self):
        response_500 = custom_500(self.mdm_request)
        self.assertEqual(response_500.status_code, 500)
