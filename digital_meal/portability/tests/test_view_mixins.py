from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import TestCase
from django.utils import timezone
from django.views.generic import View

from digital_meal.portability.models import OAuthStateToken, TikTokAccessToken
from digital_meal.portability.tests.utils import get_request_with_session
from digital_meal.portability.views import (
    StateTokenMixin,
    ManageAccessTokenMixin,
    AuthenticationRequiredMixin,
    ActiveAccessTokenRequiredMixin
)

User = get_user_model()


class TestStateTokenMixin(TestCase):
    session_key = StateTokenMixin.state_token_session_key

    def setUp(self):

        class TestView(StateTokenMixin, View):
            pass

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request

    def test_store_state_token_in_session(self):
        test_token = 'test-token'
        self.view.store_state_token_in_session(test_token)

        token_in_session = self.request.session[self.session_key]
        self.assertEquals(token_in_session, test_token)

    def test_store_state_token_in_session_overwrites_existing(self):
        old_token = 'test-token-new'
        new_token = 'test-token-old'
        self.view.store_state_token_in_session(old_token)
        self.view.store_state_token_in_session(new_token)
        token_in_session = self.request.session[self.session_key]

        self.assertEquals(token_in_session, new_token)

    def test_get_or_create_state_token_with_existing_token(self):
        test_token = OAuthStateToken.objects.create()
        self.request.session[self.session_key] = test_token.token
        retrieved_token = self.view.get_or_create_state_token()
        self.assertEqual(retrieved_token, test_token.token)

    def test_get_or_create_state_token_with_nonexistent_token_creates_token(self):
        retrieved_token = self.view.get_or_create_state_token()
        self.assertIsNotNone(retrieved_token)
        self.assertTrue(OAuthStateToken.objects.filter(token=retrieved_token).exists())

    def test_verify_and_consume_state_token_with_valid_token(self):
        token = OAuthStateToken.objects.create()

        self.request.session[self.session_key] = token.token
        self.view.verify_and_consume_state_token(token.token)
        token.refresh_from_db()

        self.assertNotIn(self.session_key, self.request.session.keys())
        self.assertTrue(token.used)

    def test_verify_and_consume_state_token_does_not_match(self):
        token = OAuthStateToken.objects.create()
        test_token = 'test-token'
        self.request.session[self.session_key] = token.token

        self.assertRaises(
            ValidationError,
            self.view.verify_and_consume_state_token,
            test_token
        )

    def test_verify_and_consume_state_token_inexistent_token(self):
        test_token = 'test-token'
        self.request.session[self.session_key] = test_token

        self.assertRaises(
            ValidationError,
            self.view.verify_and_consume_state_token,
            test_token
        )

    def test_verify_and_consume_state_token_expired_token(self):
        token = OAuthStateToken.objects.create()
        token.created_at = timezone.now() - timedelta(days=1)
        token.save()

        self.assertRaises(
            ValidationError,
            self.view.verify_and_consume_state_token,
            token.token
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
            token='token-valid',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            open_id='test-id-a',
            token_type='bearer',
        )

        cls.expired_token = TikTokAccessToken.objects.create(
            token='token-expired',
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() - timedelta(hours=1),
            open_id='test-id-b',
            token_type='bearer',
        )

    def test_get_valid_access_token_from_db_valid(self):
        token = self.view.get_valid_access_token_from_db(self.valid_token.open_id)
        self.assertEquals(token.token, self.valid_token.token)

    def test_get_valid_access_token_from_db_nonexisting(self):
        self.assertRaises(
            TikTokAccessToken.DoesNotExist,
            self.view.get_valid_access_token_from_db,
            'nonexisting-open-id'
        )

    def test_get_valid_access_token_from_db_expired(self):
        self.assertRaises(
            ValidationError,
            self.view.get_valid_access_token_from_db,
            self.expired_token.open_id
        )

    def test_store_open_id_in_session(self):
        self.view.store_open_id_in_session(self.valid_token.open_id)
        self.assertEquals(
            self.valid_token.open_id,
            self.request.session.get(self.view.open_id_session_key)
        )

    def test_get_open_id_from_session(self):
        self.request.session[self.view.open_id_session_key] = self.valid_token.open_id
        open_id = self.view.get_open_id_from_session()
        self.assertEquals(open_id, self.valid_token.open_id)


class TestViewAuthenticationRequiredMixin(AuthenticationRequiredMixin, View):
    """ Test view that uses the AuthenticationRequiredMixin. """

    def get(self, request):
        return HttpResponse('Success')


class TestAuthenticationRequiredMixin(TestCase):

    def setUp(self):

        class TestView(AuthenticationRequiredMixin, View):
            def get(self, request):
                return HttpResponse('Success')

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request

    def test_view_with_open_id_calls_super(self):
        self.view.request.session[self.view.open_id_session_key] = 'test-id'
        response = self.view.dispatch(self.request)

        self.assertEqual(response.status_code, 200)

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_view_without_open_id_calls_redirect_to_auth_view(self, mock_redirect):
        mock_redirect.return_value = HttpResponse()
        _ = self.view.dispatch(self.request)
        mock_redirect.assert_called_once_with(self.request)


class TestActiveAccessTokenRequiredMixin(TestCase):

    def setUp(self):

        class TestView(ActiveAccessTokenRequiredMixin, View):
            def get(self, request):
                return HttpResponse('Success')

        self.view = TestView()
        self.request = get_request_with_session()
        self.view.request = self.request

    @classmethod
    def setUpTestData(cls):
        cls.token = TikTokAccessToken.objects.create(
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            open_id='test-id',
            token_type='bearer',
        )

        cls.expired_token = TikTokAccessToken.objects.create(
            token='token-expired',
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() - timedelta(hours=1),
            open_id='test-id-b',
            token_type='bearer',
        )

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_view_without_associated_access_token_calls_redirect_to_auth_view(
            self, mock_redirect
    ):
        mock_redirect.return_value = HttpResponse()

        self.view.request.session[self.view.open_id_session_key] = 'test-id-fails'
        _ = self.view.dispatch(self.request)

        mock_redirect.assert_called_once_with(self.request)

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_inactive_access_token_calls_redirect_to_auth_view(
            self,
            mock_redirect
    ):
        mock_redirect.return_value = HttpResponse()

        self.view.request.session[self.view.open_id_session_key] = 'test-id-b'
        _ = self.view.dispatch(self.request)

        mock_redirect.assert_called_once_with(self.request)

    def test_valid_access_token_calls_super(self):
        self.view.request.session[self.view.open_id_session_key] = 'test-id'
        response = self.view.dispatch(self.request)

        self.assertEqual(response.status_code, 200)
