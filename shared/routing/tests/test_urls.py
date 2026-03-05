from django.conf import settings
from django.test import TestCase, override_settings

from shared.routing.constants import MDMRoutingTypes
from shared.routing.urls import absolute_reverse, absolute_reverse_lazy

URL_SCHEME = "http://" if settings.DEBUG else "https://"


@override_settings(
    MDM_ROUTING_TYPE=MDMRoutingTypes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
    MDM_SUBDOMAIN="my.dm.com",
    MAIN_DOMAIN="dm.com",
)
class ReverseURLPrefixModeTests(TestCase):
    def test_mdm_view_returns_relative_url(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertFalse(url.startswith(URL_SCHEME))

    def test_main_view_returns_relative_url(self):
        url = absolute_reverse("newsletter")
        self.assertFalse(url.startswith(URL_SCHEME))

    def test_mdm_view_contains_prefix(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertTrue(url.startswith("/my/"))


@override_settings(
    MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MAIN_DOMAIN="dm.com",
)
class ReverseSubdomainModeTests(TestCase):
    def test_mdm_view_returns_absolute_url(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertTrue(url.startswith(f"{URL_SCHEME}my.dm.com/"))

    def test_main_view_returns_absolute_url(self):
        url = absolute_reverse("newsletter")
        self.assertTrue(url.startswith(f"{URL_SCHEME}dm.com/"))

    def test_mdm_view_does_not_contain_main_domain(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertNotIn("dm.com/", url.replace("my.dm.com", ""))

    def test_main_view_does_not_contain_mdm_subdomain(self):
        url = absolute_reverse("newsletter")
        self.assertNotIn("my.dm.com", url)


@override_settings(
    MDM_ROUTING_TYPE=MDMRoutingTypes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MAIN_DOMAIN="dm.com",
)
class ReverseLazySubdomainModeTests(TestCase):
    def test_mdm_view_is_lazy(self):
        url = absolute_reverse_lazy("mdm:userflow:landing_page")
        # Should not have evaluated yet — still a lazy object
        self.assertNotIsInstance(url, str)

    def test_mdm_view_evaluates_to_absolute_url(self):
        url = str(absolute_reverse_lazy("mdm:userflow:landing_page"))
        self.assertTrue(url.startswith(f"{URL_SCHEME}my.dm.com/"))

    def test_main_view_evaluates_to_absolute_url(self):
        url = str(absolute_reverse_lazy("newsletter"))
        self.assertTrue(url.startswith(f"{URL_SCHEME}dm.com/"))


@override_settings(
    MDM_ROUTING_TYPE=MDMRoutingTypes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
    MDM_SUBDOMAIN="my.dm.com",
    MAIN_DOMAIN="dm.com",
)
class ReverseLazyURLPrefixModeTests(TestCase):
    def test_mdm_view_evaluates_to_relative_url(self):
        url = str(absolute_reverse_lazy("mdm:userflow:landing_page"))
        self.assertFalse(url.startswith(URL_SCHEME))

    def test_main_view_evaluates_to_relative_url(self):
        url = str(absolute_reverse_lazy("newsletter"))
        self.assertFalse(url.startswith(URL_SCHEME))
