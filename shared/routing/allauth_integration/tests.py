from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.template import TemplateDoesNotExist
from django.test import RequestFactory, TestCase, override_settings

from digital_meal.tool.models import Teacher
from shared.routing.allauth_integration.adapters import SubdomainAccountAdapter
from shared.routing.allauth_integration.context import current_request_var
from shared.routing.allauth_integration.middleware import SubdomainAuthMiddleware
from shared.routing.allauth_integration.sessions import AuthSession, AuthSessionManager
from shared.routing.allauth_integration.settings import AuthContexts
from shared.routing.constants import MDMRoutingModes

User = get_user_model()


def _get_request_with_session(path="/"):
    factory = RequestFactory()
    request = factory.get(path)
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    return request


# AuthSession ------------------------------------------------------------------


class TestAuthSession(TestCase):
    def test_default_auth_context_is_none(self):
        session = AuthSession()
        self.assertIsNone(session.auth_context)

    def test_string_context_is_converted_to_enum(self):
        session = AuthSession(auth_context="digital_meal")
        self.assertIsInstance(session.auth_context, AuthContexts)
        self.assertEqual(session.auth_context, AuthContexts.DM_EDUCATION)

    def test_none_context_is_left_unchanged(self):
        session = AuthSession(auth_context=None)
        self.assertIsNone(session.auth_context)

    def test_enum_context_is_left_unchanged(self):
        session = AuthSession(auth_context=AuthContexts.MY_DM)
        self.assertEqual(session.auth_context, AuthContexts.MY_DM)

    def test_to_session_dict_serialises_enum_to_value(self):
        session = AuthSession(auth_context=AuthContexts.DM_EDUCATION)
        self.assertEqual(session.to_session_dict(), {"auth_context": "digital_meal"})

    def test_to_session_dict_with_none_context(self):
        session = AuthSession(auth_context=None)
        self.assertEqual(session.to_session_dict(), {"auth_context": None})


# AuthSessionManager -----------------------------------------------------------


class TestAuthSessionManager(TestCase):
    def setUp(self):
        self.request = _get_request_with_session()
        self.manager = AuthSessionManager.from_request(self.request)

    def _seed_session(self, **kwargs):
        data = {"auth_context": None}
        data.update(kwargs)
        self.request.session[AuthSessionManager.SESSION_KEY] = data
        self.request.session.save()

    # --- from_request ---

    def test_from_request_returns_manager_instance(self):
        manager = AuthSessionManager.from_request(self.request)
        self.assertIsInstance(manager, AuthSessionManager)

    # --- get ---

    def test_get_returns_none_when_session_absent(self):
        self.assertIsNone(self.manager.get())

    def test_get_returns_auth_session_when_present(self):
        self._seed_session(auth_context="digital_meal")
        result = self.manager.get()
        self.assertIsInstance(result, AuthSession)
        self.assertEqual(result.auth_context, AuthContexts.DM_EDUCATION)

    # --- initialize ---

    def test_initialize_creates_session_when_absent(self):
        self.assertNotIn(AuthSessionManager.SESSION_KEY, self.request.session)
        self.manager.initialize()
        self.assertIn(AuthSessionManager.SESSION_KEY, self.request.session)

    def test_initialize_returns_existing_session_when_present(self):
        self._seed_session(auth_context="mydigitalmeal")
        result = self.manager.initialize()
        self.assertEqual(result.auth_context, AuthContexts.MY_DM)

    # --- get_auth_context ---

    def test_get_auth_context_returns_none_when_session_absent(self):
        self.assertIsNone(self.manager.get_auth_context())

    def test_get_auth_context_returns_enum_when_session_present(self):
        self._seed_session(auth_context="digital_meal")
        self.assertEqual(self.manager.get_auth_context(), AuthContexts.DM_EDUCATION)

    # --- update ---

    def test_update_creates_session_when_absent(self):
        self.manager.update(auth_context=AuthContexts.MY_DM)
        self.assertEqual(self.manager.get_auth_context(), AuthContexts.MY_DM)

    def test_update_changes_auth_context(self):
        self._seed_session(auth_context="digital_meal")
        self.manager.update(auth_context=AuthContexts.MY_DM)
        self.assertEqual(self.manager.get_auth_context(), AuthContexts.MY_DM)

    def test_update_marks_session_as_modified(self):
        self.manager.update(auth_context=AuthContexts.DM_EDUCATION)
        self.assertTrue(self.request.session.modified)

    # --- reset ---

    def test_reset_clears_auth_context(self):
        self._seed_session(auth_context="digital_meal")
        result = self.manager.reset()
        self.assertIsNone(result.auth_context)

    # --- delete ---

    def test_delete_removes_session_key(self):
        self._seed_session()
        self.manager.delete()
        self.assertNotIn(AuthSessionManager.SESSION_KEY, self.request.session)

    def test_delete_is_noop_when_session_absent(self):
        self.manager.delete()  # must not raise


# SubdomainAuthMiddleware - should_enforce_context_change ----------------------


class TestShouldEnforceContextChange(TestCase):
    def setUp(self):
        self.middleware = SubdomainAuthMiddleware(get_response=lambda r: None)

    def test_returns_false_when_curr_context_is_my_dm(self):
        result = self.middleware.should_enforce_context_change(
            AuthContexts.DM_EDUCATION, AuthContexts.MY_DM
        )
        self.assertFalse(result)

    def test_returns_false_when_no_prev_context_and_curr_is_my_dm(self):
        result = self.middleware.should_enforce_context_change(None, AuthContexts.MY_DM)
        self.assertFalse(result)

    def test_returns_false_when_contexts_are_equal(self):
        result = self.middleware.should_enforce_context_change(
            AuthContexts.DM_EDUCATION, AuthContexts.DM_EDUCATION
        )
        self.assertFalse(result)

    def test_returns_true_when_switching_from_my_dm_to_dm_education(self):
        result = self.middleware.should_enforce_context_change(
            AuthContexts.MY_DM, AuthContexts.DM_EDUCATION
        )
        self.assertTrue(result)

    def test_returns_false_when_no_prev_context_and_curr_is_dm_education(self):
        result = self.middleware.should_enforce_context_change(
            None, AuthContexts.DM_EDUCATION
        )
        self.assertFalse(result)


# SubdomainAuthMiddleware - should_logout_user ---------------------------------


class TestShouldLogoutUser(TestCase):
    def setUp(self):
        self.middleware = SubdomainAuthMiddleware(get_response=lambda r: None)

    def test_returns_false_for_anonymous_user(self):
        user = MagicMock()
        user.is_authenticated = False
        self.assertFalse(self.middleware.should_logout_user(user))

    def test_returns_false_for_staff_user(self):
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff = True
        self.assertFalse(self.middleware.should_logout_user(user))

    def test_returns_false_for_user_with_teacher_profile(self):
        user = User.objects.create_user(
            username="teacher", password="pass", email="t@t.com"
        )
        Teacher.objects.create(user=user, name="Muster", first_name="Max", canton="AG")
        self.assertFalse(self.middleware.should_logout_user(user))

    def test_returns_true_for_authenticated_user_without_teacher_profile(self):
        user = User.objects.create_user(
            username="regular", password="pass", email="r@r.com"
        )
        self.assertTrue(self.middleware.should_logout_user(user))


# SubdomainAuthMiddleware - should_use_mdm_context -----------------------------


class TestShouldUseMDMContext(TestCase):
    def setUp(self):
        self.middleware = SubdomainAuthMiddleware(get_response=lambda r: None)

    @override_settings(
        MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX, MDM_URL_PREFIX="my/"
    )
    def test_returns_true_for_mdm_url_prefix(self):
        request = _get_request_with_session("/my/dashboard/")
        result = self.middleware.should_use_mdm_context(request)
        self.assertTrue(result)

    @override_settings(
        MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX, MDM_URL_PREFIX="my/"
    )
    def test_returns_false_for_non_mdm_url_prefix(self):
        request = _get_request_with_session("/dashboard/")
        result = self.middleware.should_use_mdm_context(request)
        self.assertFalse(result)

    @override_settings(
        ALLOWED_HOSTS=["my.site.com", "site.com"],
        MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.site.com",
    )
    def test_returns_true_for_mdm_subdomain(self):
        request = _get_request_with_session("/dashboard/")
        request.META["HTTP_HOST"] = "my.site.com"
        result = self.middleware.should_use_mdm_context(request)
        self.assertTrue(result)

    @override_settings(
        ALLOWED_HOSTS=["my.site.com", "site.com"],
        MDM_ROUTING_MODE=MDMRoutingModes.SUBDOMAIN,
        MDM_SUBDOMAIN="my.site.com",
    )
    def test_returns_false_for_non_mdm_subdomain(self):
        request = _get_request_with_session("/dashboard/")
        request.META["HTTP_HOST"] = "site.com"
        result = self.middleware.should_use_mdm_context(request)
        self.assertFalse(result)


# SubdomainAuthMiddleware - __call__  ------------------------------------------


@override_settings(MDM_ROUTING_MODE=MDMRoutingModes.URL_PREFIX, MDM_URL_PREFIX="my/")
class TestSubdomainAuthMiddlewareCall(TestCase):
    def setUp(self):
        self.get_response = MagicMock(return_value=MagicMock())
        self.middleware = SubdomainAuthMiddleware(get_response=self.get_response)

    def test_sets_my_dm_template_prefix_for_my_path(self):
        request = _get_request_with_session("/my/dashboard/")
        self.middleware(request)
        self.assertEqual(request.template_prefix, AuthContexts.MY_DM)

    def test_sets_dm_education_template_prefix_for_non_my_path(self):
        request = _get_request_with_session("/education/")
        request.user = AnonymousUser()
        self.middleware(request)
        self.assertEqual(request.template_prefix, AuthContexts.DM_EDUCATION)

    def test_session_auth_context_updated_to_my_dm(self):
        request = _get_request_with_session("/my/")
        self.middleware(request)
        ctx = AuthSessionManager.from_request(request).get_auth_context()
        self.assertEqual(ctx, AuthContexts.MY_DM)

    def test_session_auth_context_updated_to_dm_education(self):
        request = _get_request_with_session("/")
        request.user = AnonymousUser()
        self.middleware(request)
        ctx = AuthSessionManager.from_request(request).get_auth_context()
        self.assertEqual(ctx, AuthContexts.DM_EDUCATION)

    def test_current_request_var_is_set(self):
        request = _get_request_with_session("/my/")
        self.middleware(request)
        self.assertIs(current_request_var.get(), request)

    def test_get_response_is_called(self):
        request = _get_request_with_session("/")
        request.user = AnonymousUser()
        self.middleware(request)
        self.get_response.assert_called_once_with(request)

    def test_logs_out_user_without_teacher_on_switch_to_dm_education(self):
        user = User.objects.create_user(
            username="u1", password="pass", email="u1@u.com"
        )
        request = _get_request_with_session("/education/")
        request.user = user
        AuthSessionManager.from_request(request).update(auth_context=AuthContexts.MY_DM)

        with patch(
            "shared.routing.allauth_integration.middleware.logout"
        ) as mock_logout:
            self.middleware(request)
            mock_logout.assert_called_once_with(request)

    def test_does_not_logout_teacher_on_context_switch(self):
        user = User.objects.create_user(
            username="u2", password="pass", email="u2@u.com"
        )
        Teacher.objects.create(user=user, name="Muster", first_name="Max", canton="AG")
        request = _get_request_with_session("/education/")
        request.user = user
        AuthSessionManager.from_request(request).update(auth_context=AuthContexts.MY_DM)

        with patch(
            "shared.routing.allauth_integration.middleware.logout"
        ) as mock_logout:
            self.middleware(request)
            mock_logout.assert_not_called()

    def test_does_not_logout_when_navigating_to_my_dm(self):
        user = User.objects.create_user(
            username="u3", password="pass", email="u3@u.com"
        )
        request = _get_request_with_session("/my/")
        request.user = user
        AuthSessionManager.from_request(request).update(
            auth_context=AuthContexts.DM_EDUCATION
        )

        with patch(
            "shared.routing.allauth_integration.middleware.logout"
        ) as mock_logout:
            self.middleware(request)
            mock_logout.assert_not_called()


# SubdomainAccountAdapter  -----------------------------------------------------

MDM_TEST_SETTINGS = {
    "ACCOUNT_LOGOUT_REDIRECT_URL": "/my/",
    "ACCOUNT_EMAIL_SUBJECT_PREFIX": "My Digital Meal | ",
}


class TestSubdomainAccountAdapter(TestCase):
    def setUp(self):
        self.adapter = SubdomainAccountAdapter(request=MagicMock())
        current_request_var.set(None)

    def tearDown(self):
        current_request_var.set(None)

    def _dm_education_request(self):
        request = MagicMock()
        request.template_prefix = AuthContexts.DM_EDUCATION
        return request

    def _my_dm_request(self):
        request = MagicMock()
        request.template_prefix = AuthContexts.MY_DM
        return request

    # --- _is_dm_education ---

    def test_is_dm_education_true_for_dm_education_context(self):
        self.assertTrue(self.adapter._is_dm_education(self._dm_education_request()))

    def test_is_dm_education_false_for_my_dm_context(self):
        self.assertFalse(self.adapter._is_dm_education(self._my_dm_request()))

    def test_is_dm_education_false_when_no_prefix_attribute(self):
        request = MagicMock(spec=[])
        self.assertFalse(self.adapter._is_dm_education(request))

    # --- _get_domain_template_prefix ---

    def test_get_domain_template_prefix_returns_prefix_attribute(self):
        request = self._my_dm_request()
        self.assertEqual(
            self.adapter._get_domain_template_prefix(request),
            AuthContexts.MY_DM,
        )

    def test_get_domain_template_prefix_returns_empty_string_when_missing(self):
        request = MagicMock(spec=[])
        self.assertEqual(self.adapter._get_domain_template_prefix(request), "")

    # --- _get_setting ---

    def test_get_setting_returns_mdm_value_for_my_dm_context(self):
        request = self._my_dm_request()
        with patch(
            "shared.routing.allauth_integration.adapters.MDM_SETTINGS",
            MDM_TEST_SETTINGS,
        ):
            result = self.adapter._get_setting("ACCOUNT_LOGOUT_REDIRECT_URL", request)
        self.assertEqual(result, "/my/")

    @override_settings(ACCOUNT_LOGOUT_REDIRECT_URL="/dm/logout/")
    def test_get_setting_returns_django_setting_for_dm_education_context(self):
        request = self._dm_education_request()
        result = self.adapter._get_setting("ACCOUNT_LOGOUT_REDIRECT_URL", request)
        self.assertEqual(result, "/dm/logout/")

    # --- get_logout_redirect_url ---

    def test_get_logout_redirect_url_returns_mdm_value_for_my_dm(self):
        request = self._my_dm_request()
        with patch(
            "shared.routing.allauth_integration.adapters.MDM_SETTINGS",
            MDM_TEST_SETTINGS,
        ):
            result = self.adapter.get_logout_redirect_url(request)
        self.assertEqual(result, "/my/")

    @override_settings(ACCOUNT_LOGOUT_REDIRECT_URL="/dm/logout/")
    def test_get_logout_redirect_url_returns_django_setting_for_dm_education(self):
        request = self._dm_education_request()
        result = self.adapter.get_logout_redirect_url(request)
        self.assertEqual(result, "/dm/logout/")

    # --- format_email_subject ---

    def test_format_email_subject_prepends_mdm_prefix_for_my_dm(self):
        request = self._my_dm_request()
        current_request_var.set(request)
        with patch(
            "shared.routing.allauth_integration.adapters.MDM_SETTINGS",
            MDM_TEST_SETTINGS,
        ):
            result = self.adapter.format_email_subject("Welcome")
        self.assertEqual(result, "My Digital Meal | Welcome")

    @override_settings(ACCOUNT_EMAIL_SUBJECT_PREFIX="[DM] ")
    def test_format_email_subject_prepends_django_setting_prefix_for_dm_education(self):
        request = self._dm_education_request()
        current_request_var.set(request)
        result = self.adapter.format_email_subject("Welcome")
        self.assertEqual(result, "[DM] Welcome")

    # --- send_mail ---

    def test_send_mail_uses_domain_template_when_it_exists(self):
        request = self._my_dm_request()
        current_request_var.set(request)

        with (
            patch.object(
                self.adapter,
                "_get_domain_template_prefix",
                return_value="mydigitalmeal",
            ),
            patch("shared.routing.allauth_integration.adapters.get_current_site"),
            patch(
                "shared.routing.allauth_integration.adapters.get_template"
            ) as mock_get_template,
            patch.object(self.adapter, "render_mail") as mock_render_mail,
        ):
            mock_render_mail.return_value = MagicMock()

            self.adapter.send_mail(
                "account/email/email_confirmation", "test@example.com", {}
            )

        mock_get_template.assert_called_once_with(
            "mydigitalmeal/account/email/email_confirmation_message.txt"
        )
        rendered_prefix = mock_render_mail.call_args[0][0]
        self.assertEqual(
            rendered_prefix, "mydigitalmeal/account/email/email_confirmation"
        )
        mock_render_mail.return_value.send.assert_called_once()

    def test_send_mail_falls_back_to_default_when_domain_template_missing(self):
        request = self._my_dm_request()
        current_request_var.set(request)

        with (
            patch.object(
                self.adapter,
                "_get_domain_template_prefix",
                return_value="mydigitalmeal",
            ),
            patch("shared.routing.allauth_integration.adapters.get_current_site"),
            patch(
                "shared.routing.allauth_integration.adapters.get_template",
                side_effect=TemplateDoesNotExist("x"),
            ),
            patch.object(self.adapter, "render_mail") as mock_render_mail,
        ):
            mock_render_mail.return_value = MagicMock()

            self.adapter.send_mail(
                "account/email/email_confirmation", "test@example.com", {}
            )

        rendered_prefix = mock_render_mail.call_args[0][0]
        self.assertEqual(rendered_prefix, "account/email/email_confirmation")
        mock_render_mail.return_value.send.assert_called_once()

    def test_send_mail_skips_domain_lookup_when_no_prefix(self):
        request = self._dm_education_request()
        current_request_var.set(request)

        with (
            patch.object(self.adapter, "_get_domain_template_prefix", return_value=""),
            patch("shared.routing.allauth_integration.adapters.get_current_site"),
            patch(
                "shared.routing.allauth_integration.adapters.get_template"
            ) as mock_get_template,
            patch.object(self.adapter, "render_mail") as mock_render_mail,
        ):
            mock_render_mail.return_value = MagicMock()

            self.adapter.send_mail(
                "account/email/email_confirmation", "test@example.com", {}
            )

        mock_get_template.assert_not_called()
        rendered_prefix = mock_render_mail.call_args[0][0]
        self.assertEqual(rendered_prefix, "account/email/email_confirmation")
        mock_render_mail.return_value.send.assert_called_once()

    def test_send_mail_context_includes_email_and_current_site(self):
        request = self._dm_education_request()
        current_request_var.set(request)
        mock_site = MagicMock()

        with (
            patch.object(self.adapter, "_get_domain_template_prefix", return_value=""),
            patch(
                "shared.routing.allauth_integration.adapters.get_current_site",
                return_value=mock_site,
            ),
            patch.object(self.adapter, "render_mail") as mock_render_mail,
        ):
            mock_render_mail.return_value = MagicMock()

            self.adapter.send_mail(
                "account/email/email_confirmation", "test@example.com", {}
            )

        _, called_email, ctx = mock_render_mail.call_args[0]
        self.assertEqual(called_email, "test@example.com")
        self.assertEqual(ctx["email"], "test@example.com")
        self.assertEqual(ctx["current_site"], mock_site)
