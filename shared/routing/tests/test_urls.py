import uuid

from django.conf import settings
from django.test import TestCase, override_settings

from shared.routing.constants import MDMRoutingModes
from shared.routing.urls import (
    _build_absolute_url,
    absolute_reverse,
    absolute_reverse_lazy,
)

URL_SCHEME = settings.MDM_ROUTING_SCHEME

# An MDM URL with a UUID kwarg (``resume/<uuid:request_id>``) — used to
# exercise positional/keyword URL argument forwarding. Lives in
# ``mydigitalmeal.userflow.urls``.
_MDM_VIEW_WITH_ARG = "mdm:userflow:resume"


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseURLPrefixModeTests(TestCase):
    def test_mdm_view_returns_relative_url(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertFalse(url.startswith(URL_SCHEME))

    def test_main_view_returns_relative_url(self):
        url = absolute_reverse("newsletter")
        self.assertFalse(url.startswith(URL_SCHEME))


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseSubdomainModeTests(TestCase):
    def test_mdm_view_returns_absolute_url(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))

    def test_main_view_returns_absolute_url(self):
        url = absolute_reverse("newsletter")
        self.assertTrue(url.startswith(f"{URL_SCHEME}://dm.com/"))

    def test_mdm_view_does_not_contain_main_domain(self):
        url = absolute_reverse("mdm:userflow:landing_page")
        self.assertNotIn("dm.com/", url.replace("my.dm.com", ""))

    def test_main_view_does_not_contain_mdm_subdomain(self):
        url = absolute_reverse("newsletter")
        self.assertNotIn("my.dm.com", url)


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseLazySubdomainModeTests(TestCase):
    def test_mdm_view_is_lazy(self):
        url = absolute_reverse_lazy("mdm:userflow:landing_page")
        # Should not have evaluated yet — still a lazy object
        self.assertNotIsInstance(url, str)

    def test_mdm_view_evaluates_to_absolute_url(self):
        url = str(absolute_reverse_lazy("mdm:userflow:landing_page"))
        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))

    def test_main_view_evaluates_to_absolute_url(self):
        url = str(absolute_reverse_lazy("newsletter"))
        self.assertTrue(url.startswith(f"{URL_SCHEME}://dm.com/"))


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseLazyURLPrefixModeTests(TestCase):
    def test_mdm_view_evaluates_to_relative_url(self):
        url = str(absolute_reverse_lazy("mdm:userflow:landing_page"))
        self.assertFalse(url.startswith(URL_SCHEME))

    def test_main_view_evaluates_to_relative_url(self):
        url = str(absolute_reverse_lazy("newsletter"))
        self.assertFalse(url.startswith(URL_SCHEME))


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX,
    MDM_URL_PREFIX="my/",
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseURLPrefixModeArgsAndQueryTests(TestCase):
    """URL_PREFIX mode: args/kwargs/query forwarded correctly to reverse()."""

    def setUp(self):
        self.request_id = uuid.uuid4()

    def test_forwards_positional_args(self):
        url = absolute_reverse(_MDM_VIEW_WITH_ARG, self.request_id)

        self.assertIn(str(self.request_id), url)

    def test_forwards_keyword_url_args(self):
        url = absolute_reverse(_MDM_VIEW_WITH_ARG, request_id=self.request_id)

        self.assertIn(str(self.request_id), url)

    def test_appends_query_string(self):
        url = absolute_reverse(
            "mdm:userflow:landing_page",
            query={"utm_source": "email", "utm_campaign": "spring"},
        )

        self.assertIn("?", url)
        self.assertIn("utm_source=email", url)
        self.assertIn("utm_campaign=spring", url)

    def test_query_with_multivalued_keys(self):
        url = absolute_reverse(
            "mdm:userflow:landing_page",
            query={"tag": ["a", "b"]},
        )

        # urlencode(doseq=True) emits ``tag=a&tag=b``, not ``tag=['a', 'b']``.
        self.assertIn("tag=a", url)
        self.assertIn("tag=b", url)
        self.assertNotIn("%5B", url)

    def test_combines_url_kwarg_and_query(self):
        url = absolute_reverse(
            _MDM_VIEW_WITH_ARG,
            request_id=self.request_id,
            query={"step": "1"},
        )

        self.assertIn(str(self.request_id), url)
        self.assertIn("?step=1", url)


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseSubdomainModeArgsAndQueryTests(TestCase):
    """SUBDOMAIN mode regression tests."""

    def setUp(self):
        self.request_id = uuid.uuid4()

    def test_positional_url_arg_preserved_in_subdomain_url(self):
        url = absolute_reverse(_MDM_VIEW_WITH_ARG, self.request_id)

        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))
        self.assertIn(str(self.request_id), url)

    def test_keyword_url_arg_preserved_in_subdomain_url(self):
        url = absolute_reverse(_MDM_VIEW_WITH_ARG, request_id=self.request_id)

        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))
        self.assertIn(str(self.request_id), url)

    def test_query_string_appended_after_domain(self):
        url = absolute_reverse(
            "mdm:userflow:landing_page",
            query={"utm_source": "email"},
        )

        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))
        self.assertTrue(url.endswith("?utm_source=email"))

    def test_combines_url_arg_and_query(self):
        url = absolute_reverse(
            _MDM_VIEW_WITH_ARG,
            request_id=self.request_id,
            query={"step": "1"},
        )

        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))
        self.assertIn(str(self.request_id), url)
        self.assertIn("?step=1", url)

    def test_build_absolute_url_handles_path_with_query(self):
        """`_build_absolute_url` isn't part of the public API, but if a
        future caller passes a path with a query string already baked in,
        the trailing-slash normalisation must touch the path portion only
        — not the query — so we don't end up with
        ``/some?abc=124/`` (slash inside the query string).
        """
        result = _build_absolute_url(
            "/some?abc=124",
            "mdm:userflow:landing_page",
        )

        self.assertEqual(
            result,
            f"{URL_SCHEME}://my.dm.com/some/?abc=124",
        )

    def test_build_absolute_url_handles_path_with_fragment(self):
        result = _build_absolute_url(
            "/some#section",
            "mdm:userflow:landing_page",
        )

        self.assertEqual(
            result,
            f"{URL_SCHEME}://my.dm.com/some/#section",
        )


@override_settings(
    MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
    MDM_SUBDOMAIN="my.dm.com",
    MDM_MAIN_DOMAIN="dm.com",
)
class ReverseLazySubdomainModeArgsAndQueryTests(TestCase):
    def setUp(self):
        self.request_id = uuid.uuid4()

    def test_lazy_preserves_positional_url_arg(self):
        url = str(absolute_reverse_lazy(_MDM_VIEW_WITH_ARG, self.request_id))

        self.assertTrue(url.startswith(f"{URL_SCHEME}://my.dm.com/"))
        self.assertIn(str(self.request_id), url)

    def test_lazy_appends_query_string(self):
        url = str(
            absolute_reverse_lazy(
                "mdm:userflow:landing_page",
                query={"utm_source": "email"},
            ),
        )

        self.assertTrue(url.endswith("?utm_source=email"))
