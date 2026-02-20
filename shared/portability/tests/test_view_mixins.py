from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import TestCase
from django.utils import timezone
from django.views import View

from shared.portability.models import OAuthStateToken, TikTokAccessToken
from shared.portability.sessions import (
    PortabilitySessionManager,
    PortabilitySessionMixin,
)
from shared.portability.tests.utils import get_request_with_session
from shared.portability.views import (
    ActiveAccessTokenRequiredMixin,
    AuthenticationRequiredMixin,
    ManageAccessTokenMixin,
    StateTokenMixin,
)

User = get_user_model()


class TestStateTokenMixin(TestCase):
    def setUp(self):
        class TestView(PortabilitySessionMixin, StateTokenMixin, View):
            pass

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request
        self.view.port_session = PortabilitySessionManager.from_request(self.request)

    def test_get_or_create_state_token_returns_existing_valid_token(self):
        token = OAuthStateToken.objects.create()
        self.view.port_session.update(state_token=token.token)

        retrieved_token = self.view.get_or_create_state_token(self.request)

        self.assertEqual(retrieved_token, token)

    def test_get_or_create_state_token_creates_token_when_none_exists(self):
        token = self.view.get_or_create_state_token(self.request)

        self.assertIsNotNone(token)
        self.assertTrue(OAuthStateToken.objects.filter(token=token.token).exists())

    def test_get_or_create_state_token_creates_new_token_when_existing_is_expired(self):
        token = OAuthStateToken.objects.create()
        token.created_at = timezone.now() - timedelta(days=1)
        token.save()
        self.view.port_session.update(state_token=token.token)

        new_token = self.view.get_or_create_state_token(self.request)

        self.assertNotEqual(new_token.token, token.token)

    def test_get_or_create_state_token_creates_new_token_when_existing_is_used(self):
        token = OAuthStateToken.objects.create()
        token.used = True
        token.save()
        self.view.port_session.update(state_token=token.token)

        new_token = self.view.get_or_create_state_token(self.request)

        self.assertNotEqual(new_token.token, token.token)

    def test_verify_and_consume_state_token_with_valid_token(self):
        token = OAuthStateToken.objects.create()
        self.view.port_session.update(state_token=token.token)

        self.view.verify_and_consume_state_token(token.token)
        token.refresh_from_db()

        self.assertIsNone(self.view.port_session.get_token())
        self.assertTrue(token.used)

    def test_verify_and_consume_state_token_does_not_match(self):
        token = OAuthStateToken.objects.create()
        self.view.port_session.update(state_token=token.token)

        self.assertRaises(
            ValidationError, self.view.verify_and_consume_state_token, "wrong-token"
        )

    def test_verify_and_consume_state_token_inexistent_token(self):
        self.view.port_session.update(state_token="nonexistent-token")

        self.assertRaises(
            ValidationError,
            self.view.verify_and_consume_state_token,
            "nonexistent-token",
        )

    def test_verify_and_consume_state_token_expired_token(self):
        token = OAuthStateToken.objects.create()
        token.created_at = timezone.now() - timedelta(days=1)
        token.save()
        self.view.port_session.update(state_token=token.token)

        self.assertRaises(
            ValidationError, self.view.verify_and_consume_state_token, token.token
        )


class TestManageAccessTokenMixin(TestCase):
    def setUp(self):
        class TestView(ManageAccessTokenMixin, View):
            pass

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request

    @classmethod
    def setUpTestData(cls):
        cls.valid_token = TikTokAccessToken.objects.create(
            token="token-valid",
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            open_id="test-id-a",
            token_type="bearer",
        )

        cls.expired_token = TikTokAccessToken.objects.create(
            token="token-expired",
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=timezone.now() - timedelta(hours=1),
            open_id="test-id-b",
            token_type="bearer",
        )

    def test_get_valid_access_token_from_db_valid(self):
        token = self.view.get_valid_access_token_from_db(self.valid_token.open_id)

        self.assertEqual(token.token, self.valid_token.token)

    def test_get_valid_access_token_from_db_nonexisting(self):
        self.assertRaises(
            TikTokAccessToken.DoesNotExist,
            self.view.get_valid_access_token_from_db,
            "nonexisting-open-id",
        )

    def test_get_valid_access_token_from_db_expired(self):
        self.assertRaises(
            ValidationError,
            self.view.get_valid_access_token_from_db,
            self.expired_token.open_id,
        )


class TestAuthenticationRequiredMixin(TestCase):
    def setUp(self):
        class TestView(AuthenticationRequiredMixin, PortabilitySessionMixin, View):
            def get(self, request):
                return HttpResponse("Success")

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request
        self.view.port_session = PortabilitySessionManager.from_request(self.request)

    def test_view_with_open_id_calls_super(self):
        self.view.port_session.update(tiktok_open_id="test-id")

        response = self.view.dispatch(self.request)

        self.assertEqual(response.status_code, 200)

    @patch("shared.portability.views.redirect_to_auth_view")
    def test_view_without_open_id_calls_redirect_to_auth_view(self, mock_redirect):
        mock_redirect.return_value = HttpResponse()

        _ = self.view.dispatch(self.request)

        mock_redirect.assert_called_once_with(self.request)


class TestActiveAccessTokenRequiredMixin(TestCase):
    def setUp(self):
        class TestView(ActiveAccessTokenRequiredMixin, PortabilitySessionMixin, View):
            def get(self, request):
                return HttpResponse("Success")

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request
        self.view.port_session = PortabilitySessionManager.from_request(self.request)

    @classmethod
    def setUpTestData(cls):
        cls.token = TikTokAccessToken.objects.create(
            token="token",
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            open_id="test-id",
            token_type="bearer",
        )

        cls.expired_token = TikTokAccessToken.objects.create(
            token="token-expired",
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token="refresh_token",
            refresh_token_expiration_date=timezone.now() - timedelta(hours=1),
            open_id="test-id-b",
            token_type="bearer",
        )

    @patch("shared.portability.views.redirect_to_auth_view")
    def test_view_without_associated_access_token_calls_redirect_to_auth_view(
        self, mock_redirect
    ):
        mock_redirect.return_value = HttpResponse()
        self.view.port_session.update(tiktok_open_id="test-id-fails")

        _ = self.view.dispatch(self.request)

        mock_redirect.assert_called_once_with(self.request)

    @patch("shared.portability.views.redirect_to_auth_view")
    def test_inactive_access_token_calls_redirect_to_auth_view(self, mock_redirect):
        mock_redirect.return_value = HttpResponse()
        self.view.port_session.update(tiktok_open_id="test-id-b")

        _ = self.view.dispatch(self.request)

        mock_redirect.assert_called_once_with(self.request)

    def test_valid_access_token_calls_super(self):
        self.view.port_session.update(tiktok_open_id="test-id")

        response = self.view.dispatch(self.request)

        self.assertEqual(response.status_code, 200)
