from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.utils import timezone
from django.views.generic import View

from digital_meal.portability.models import OAuthToken, TikTokAccessToken
from digital_meal.portability.views import StateTokenMixin, TikTokCallbackView, AccessTokenMixin

User = get_user_model()


class TestView(StateTokenMixin, View):
    """ Test view that uses the StateTokenMixin. """
    pass

class TestStateTokenMixin(TestCase):

    def setUp(self):
        """ Set up test dependencies. """
        self.factory = RequestFactory()
        self.view = TestView()

        # Create a request with session support
        self.request = self.factory.get('/')

        # Add session middleware to the request
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(self.request)
        self.request.session.save()

        # Attach request to view
        self.view.request = self.request

    def test_store_state_token_in_session(self):
        """ Test that store_state_token_in_session stores token in session. """
        test_token = 'test123'
        self.view.store_state_token_in_session(test_token)
        token_in_session = self.request.session['state_token']

        self.assertEquals(token_in_session, test_token)

    def test_store_state_token_in_session_with_custom_key(self):
        """
        Test that store_state_token_in_session stores token in session with
        custom key.
        """
        test_token = 'test123'
        session_key = 'custom_key'
        self.view.store_state_token_in_session(test_token, session_key)
        token_in_session = self.request.session[session_key]

        self.assertEquals(token_in_session, test_token)

    def test_store_state_token_in_session_overwrites_existing(self):
        """ Test that store_state_token_in_session overwrites existing token. """
        old_token = 'test123'
        new_token = 'test456'
        self.view.store_state_token_in_session(old_token)
        self.view.store_state_token_in_session(new_token)
        token_in_session = self.request.session['state_token']

        self.assertEquals(token_in_session, new_token)

    def test_get_or_create_state_token_existing_default_key(self):
        """ Test retrieving token from session with default key. """
        test_token = OAuthToken.objects.create()
        self.request.session['state_token'] = test_token.token
        retrieved_token = self.view.get_or_create_state_token()
        self.assertEqual(retrieved_token, test_token.token)

    def test_get_or_create_state_token_existing_custom_key(self):
        test_token = OAuthToken.objects.create()
        self.request.session['custom_state_token'] = test_token.token
        retrieved_token = self.view.get_or_create_state_token('custom_state_token')
        self.assertEqual(retrieved_token, test_token.token)

    def test_get_or_create_state_token_nonexistent_default_key(self):
        """ Test retrieving non-existent token returns None """
        retrieved_token = self.view.get_or_create_state_token()
        self.assertIsNotNone(retrieved_token)
        self.assertTrue(OAuthToken.objects.filter(token=retrieved_token).exists())

    def test_verify_and_consume_state_token_valid(self):
        """ Test token verification with valid token. """
        token = OAuthToken.objects.create()
        test_token = token.token

        self.request.session['state_token'] = token.token
        token_is_valid = self.view.verify_and_consume_state_token(test_token)
        token.refresh_from_db()

        self.assertTrue(token_is_valid)
        self.assertIsNone(self.request.session['state_token'])
        self.assertTrue(token.used)

    def test_verify_and_consume_state_token_invalid(self):
        """ Test token verification with invalid token. """
        token = OAuthToken.objects.create()
        test_token = 'test234'

        self.request.session['state_token'] = token.token
        try:
            self.view.verify_and_consume_state_token(test_token)
            self.fail('Token verification failed')
        except ValidationError:
            pass

        token.refresh_from_db()
        self.assertEquals(self.request.session['state_token'], token.token)
        self.assertFalse(token.used)

    def test_session_persistence(self):
        """ Test that tokens persist across session saves. """
        test_token = OAuthToken.objects.create()

        self.view.store_state_token_in_session(test_token.token)
        self.request.session.save()

        # Simulate new request with same session
        new_request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(new_request)
        new_request.session = SessionStore(session_key=self.request.session.session_key)

        new_view = TestView()
        new_view.request = new_request

        retrieved_token = new_view.get_or_create_state_token()
        self.assertEqual(retrieved_token, test_token.token)


class TestViewAccessTokenMixin(AccessTokenMixin, View):
    """ Test view that uses the StateTokenMixin. """
    pass


class TestAccessTokenMixin(TestCase):

    def setUp(self):
        """ Set up test dependencies. """
        self.factory = RequestFactory()
        self.view = TestViewAccessTokenMixin()

        # Create a request with session support
        self.request = self.factory.get('/')

        # Add session middleware to the request
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(self.request)
        self.request.session.save()

        # Attach request to view
        self.view.request = self.request

        self.valid_token = TikTokAccessToken.objects.create(
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            open_id='123',
            token_type='bearer',
        )

        self.expired_token = TikTokAccessToken.objects.create(
            token='token',
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() - timedelta(hours=1),
            open_id='456',
            token_type='bearer',
        )

    def test_get_valid_access_token_from_db_valid(self):
        """ Test that get_valid_access_token_from_db returns access token. """
        token = self.view.get_valid_access_token_from_db(self.valid_token.pk)
        self.assertEquals(token, self.valid_token.token)

    def test_get_valid_access_token_from_db_invalid(self):
        """
        Test that get_valid_access_token_from_db raises error with
        inexistent token.
        """
        try:
            self.view.get_valid_access_token_from_db(123456)
            self.fail('Access token verification failed: Did not raise DoesNotExist error.')
        except TikTokAccessToken.DoesNotExist:
            pass

    @patch.object(TikTokAccessToken, 'refresh')
    def test_get_valid_access_token_from_db_expired(self, mock_refresh):
        """
        Test that get_valid_access_token_from_db raises error with
        inexistent token.
        """
        # Mock that refresh returns None
        mock_refresh.return_value = None

        try:
            self.view.get_valid_access_token_from_db(self.expired_token.pk)
            self.fail('Access token verification failed: '
                      'Did not raise ValidationError for expired token.')
        except ValidationError:
            pass

class TestOAuthTokenModel(TestCase):

    def test_token_generation(self):
        """ Test that token is automatically generated. """
        token = OAuthToken.objects.create()
        self.assertEqual(len(token.token), 50)

    def test_token_is_expired(self):
        """ Test that .is_expired returns True if token is expired. """
        token = OAuthToken.objects.create()
        token.created_at = timezone.now() - timedelta(minutes=11)
        self.assertTrue(token.is_expired)

    def test_token_is_not_expired(self):
        """ Test that .is_expired returns False if token is not expired. """
        token = OAuthToken.objects.create()
        self.assertFalse(token.is_expired())


class TestTikTokAuthView(TestCase):

    def setUp(self):
        self.client = Client()
        self.auth_url = reverse('tiktok_auth')

    def test_auth_view_renders_correctly(self):
        response = self.client.get(self.auth_url)
        self.assertEqual(response.status_code, 200)

    def test_auth_view_creates_state_token(self):
        n_tokens_before = OAuthToken.objects.count()
        response = self.client.post(self.auth_url)

        # Check database
        n_tokens_after = OAuthToken.objects.count()
        self.assertEqual(n_tokens_before + 1, n_tokens_after)

        # Check session
        session = self.client.session
        self.assertIn('state_token', session)
        self.assertIsNotNone(session['state_token'])

        # Check that session token matches database token
        latest_token = OAuthToken.objects.latest('created_at')
        self.assertEqual(session['state_token'], latest_token.token)


class TestTikTokCallbackView(TestCase):

    def setUp(self):
        self.client = Client()
        self.callback_url = reverse('tiktok_callback')

        self.factory = RequestFactory()
        self.view = TikTokCallbackView()

    def add_session_to_request(self, request):
        """ Helper to add session to request. """
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        return request

    @patch.object(TikTokCallbackView, 'verify_and_consume_state_token')
    @patch.object(TikTokCallbackView, 'exchange_code_for_token')
    def test_callback_view_renders_correctly(self, mock_exchange, mock_verify):
        """ Test callback view behaviour when request is 'good' """
        # Patch functions
        mock_verify.return_value = True
        mock_exchange.return_value = {
            'access_token': '<PASSWORD>',
            'refresh_token': '<PASSWORD>',
            'expires_in': 3600,
            'refresh_expires_in': 3600,
            'open_id': '123',
            'scope': 'scopeA,scopeB',
            'token_type': 'bearer'
        }

        response = self.client.get(self.callback_url + '?code=code&state=state')

        # Check that correct link to access token is stored in session.
        session = self.client.session
        self.assertIn('tiktok_access_token_pk', session)
        self.assertIsNotNone(session['tiktok_access_token_pk'])

        token_pk = session['tiktok_access_token_pk']
        self.assertEquals(token_pk, TikTokAccessToken.objects.latest('created_at').pk)

        # Check that view redirects correctly.
        self.assertRedirects(response, reverse('tiktok_data_review'))

    def test_callback_view_missing_state(self):
        """ Test missing state parameter returns 400. """
        request = self.factory.get('/callback/')
        request = self.add_session_to_request(request)
        self.view.request = request

        response = self.view.dispatch(request)

        # Check response.
        self.assertEqual(response.status_code, 400)

    @patch.object(TikTokCallbackView, 'verify_and_consume_state_token')
    def test_callback_view_invalid_state_token(self, mock_verify):
        """ Test invalid state token returns 400. """
        # Mock state token verification fails.
        mock_verify.side_effect = ValidationError('')

        request = self.factory.get('/callback/?state=invalid_token')
        request = self.add_session_to_request(request)
        self.view.request = request

        response = self.view.dispatch(request)

        # Check response.
        self.assertEqual(response.status_code, 400)

    @patch.object(TikTokCallbackView, 'verify_and_consume_state_token')
    def test_callback_view_error_in_request(self, mock_verify):
        """ Test 'error' in request returns 400. """
        # Mock state token verification passes.
        mock_verify.return_value = True

        request = self.factory.get('/callback/?error=some-error')
        request = self.add_session_to_request(request)
        self.view.request = request

        response = self.view.dispatch(request)

        # Check response.
        self.assertEqual(response.status_code, 400)

    @patch.object(TikTokCallbackView, 'verify_and_consume_state_token')
    def test_callback_view_missing_code(self, mock_verify):
        """ Test missing 'code' in request returns 400. """
        # Mock state token verification passes.
        mock_verify.return_value = True

        request = self.factory.get('/callback/?state=valid_token')
        request = self.add_session_to_request(request)
        self.view.request = request

        response = self.view.dispatch(request)

        # Check response.
        self.assertEqual(response.status_code, 400)


    @patch.object(TikTokCallbackView, 'verify_and_consume_state_token')
    @patch.object(TikTokCallbackView, 'exchange_code_for_token')
    def test_callback_view_token_request_fails(self, mock_exchange, mock_verify):
        """ Test missing 'code' in request returns 400. """
        # Mock state token verification passes.
        mock_verify.return_value = True
        mock_exchange.return_value = None

        request = self.factory.get('/callback/?state=valid_token')
        request = self.add_session_to_request(request)
        self.view.request = request

        response = self.view.dispatch(request)

        # Check response.
        self.assertEqual(response.status_code, 400)
