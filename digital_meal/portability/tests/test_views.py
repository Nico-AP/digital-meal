from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import TestCase, RequestFactory, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from digital_meal.portability.models import OAuthStateToken, TikTokAccessToken, TikTokDataRequest
from digital_meal.portability.tests.utils import get_request_with_session
from digital_meal.portability.views import (
    TikTokCallbackView,
    ManageAccessTokenMixin,
    TikTokAuthView, StateTokenMixin, TikTokCheckDownloadAvailabilityView
)


User = get_user_model()


class TestTikTokAuthView(TestCase):

    def test_auth_view_200(self):
        url = reverse('tiktok_auth')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        TIKTOK_AUTH_URL='https://www.tiktok.com/auth/',
        TIKTOK_CLIENT_KEY='test-client-key-123',
        TIKTOK_REDIRECT_URL='https://www.some-url.com/callback/',
    )
    def test_build_auth_url(self):
        view = TikTokAuthView()
        view.state_token = 'mock-state'

        expected_auth_url = (
            'https://www.tiktok.com/auth/?client_key=test-client-key-123'
            '&scope=user.info.basic,portability.all.single'
            '&redirect_uri=https://www.some-url.com/callback/'
            f'&state={view.state_token}'
            '&response_type=code'
        )
        auth_url = view.build_auth_url()
        self.assertEqual(expected_auth_url, auth_url)


class TestTikTokCallbackView(TestCase):

    def setUp(self):
        class TestCallbackView(TikTokCallbackView):
            def get(self, request, *args, **kwargs):
                return HttpResponse('Success')

        self.view = TestCallbackView()
        self.request = get_request_with_session()

    @classmethod
    def setUpTestData(cls):
        state_token_obj = OAuthStateToken.objects.create()
        cls.state_token = state_token_obj.token

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_dispatch_missing_state_in_request_calls_redirect_to_auth(
            self,
            mock_redirect
    ):
        mock_redirect.return_value = HttpResponse()
        request = get_request_with_session('/callback/')
        self.view.request = request

        _ = self.view.dispatch(request)

        mock_redirect.assert_called_once_with(request)

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_dispatch_error_in_request_calls_redirect_to_auth(
            self,
            mock_redirect
    ):
        mock_redirect.return_value = HttpResponse()

        url = f'/callback/?state={self.state_token}&error=some-error'
        request = get_request_with_session(url)
        request.session[self.view.state_token_session_key] = self.state_token
        request.session.save()

        self.view.request = request
        _ = self.view.dispatch(request)

        mock_redirect.assert_called_once_with(request)

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_dispatch_missing_code_in_request_calls_redirect_to_auth(
            self,
            mock_redirect
    ):
        mock_redirect.return_value = HttpResponse()

        url = f'/callback/?state={self.state_token}'
        request = get_request_with_session(url)
        request.session[self.view.state_token_session_key] = self.state_token
        request.session.save()

        self.view.request = request
        _ = self.view.dispatch(request)

        mock_redirect.assert_called_once_with(request)

    def test_dispatch_with_valid_request(self):
        url = f'/callback/?state={self.state_token}&code=some-code'
        request = get_request_with_session(url)
        request.session[self.view.state_token_session_key] = self.state_token
        request.session.save()

        self.view.request = request
        response = self.view.dispatch(request)

        self.assertEqual(response.status_code, 200)

    @patch('digital_meal.portability.services.TikTokAccessTokenService.exchange_code_for_token')
    def test_full_flow_happy_case(self, mock_token_exchange):
        mock_token_exchange.return_value = {
            'access_token': 'test-token',
            'expires_in': 3600,
            'open_id': 'test-open-id',
            'refresh_expires_in': 3600,
            'refresh_token': 'test-refresh-token',
            'scope': 'full',
            'token_type': 'bearer'
        }

        # Initialize session
        self.client.get('/')
        session = self.client.session
        session[StateTokenMixin.state_token_session_key] = self.state_token
        session.save()

        url = reverse('tiktok_callback') + f'?state={self.state_token}&code=some-code'
        response = self.client.get(url)

        # Verify database
        self.assertTrue(TikTokAccessToken.objects.filter(open_id='test-open-id').exists())
        # Verify session
        self.assertEqual(
            self.client.session.get(self.view.open_id_session_key),
            'test-open-id'
        )
        # Verify redirect
        self.assertRedirects(response, reverse('tiktok_await_data_download'))


class TestTikTokAwaitDownloadView(TestCase):

    def setUp(self):
        self.open_id = 'test-open-id'
        self.access_token = TikTokAccessToken.objects.create(
            open_id=self.open_id,
            token='test-token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            token_type='bearer',
        )

    def test_download_await_view_200(self):
        self.client.get('/')

        session = self.client.session
        session[ManageAccessTokenMixin.open_id_session_key] = self.open_id
        session.save()

        url = reverse('tiktok_auth')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestTikTokCheckDownloadAvailabilityView(TestCase):

    def setUp(self):
        self.request_id = 1234567890
        self.open_id = 'test-open-id'
        self.access_token = TikTokAccessToken.objects.create(
            open_id=self.open_id,
            token='test-token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh_token',
            refresh_token_expiration_date=timezone.now() + timedelta(hours=1),
            token_type='bearer',
        )

        # Initialize session and store open id
        self.request = get_request_with_session()
        self.request.session[ManageAccessTokenMixin.open_id_session_key] = self.open_id
        self.request.session.save()

        self.view = TikTokCheckDownloadAvailabilityView()
        self.view.access_token = self.access_token
        self.view.request = self.request

        self.mock_poll_data = {
            'data': {
                'apply_time': 1703186989,
                'category_selection_list': [],
                'collect_time': None,
                'request_id': self.request_id,
                'status': ''
            },
            'error': {
                'code': 'ok',
                'message': '',
                'log_id': '123'
            }
        }

    def create_data_request_in_db(self):
        return TikTokDataRequest.objects.create(
            request_id=self.request_id,
            open_id=self.open_id,
        )

    @patch('digital_meal.portability.services.TikTokPortabilityAPIClient.poll_data_request_status')
    @patch('digital_meal.portability.services.TikTokPortabilityAPIClient.make_data_request')
    def test_download_await_view_creates_data_request_if_none_exists(
            self,
            mock_request_response,
            mock_poll_response,
    ):
        mock_request_response.return_value = {
            'data': {
                'request_id': self.request_id
            },
            'error': {
                'code': 'ok',
                'message': '',
                'log_id': '456'
            }
        }

        mock_data = self.mock_poll_data.copy()
        mock_data['data']['status'] = 'pending'
        mock_poll_response.return_value = mock_data

        self.assertEqual(
            TikTokDataRequest.objects.filter(request_id=self.request_id).count(),
            0
        )

        _ = self.view.get_context_data()

        self.assertEqual(
            TikTokDataRequest.objects.filter(request_id=self.request_id).count(),
            1
        )
        self.assertEqual(self.view.template_name, self.view.template_pending)

    @patch('digital_meal.portability.services.TikTokPortabilityAPIClient.poll_data_request_status')
    def test_download_await_view_with_request_status_pending(self, mock_poll_response):
        mock_data = self.mock_poll_data.copy()
        mock_data['data']['status'] = 'pending'
        mock_poll_response.return_value = mock_data

        data_request = self.create_data_request_in_db()
        _ = self.view.get_context_data()
        data_request.refresh_from_db()

        self.assertEqual(self.view.template_name, self.view.template_pending)
        self.assertEqual(data_request.status, 'pending')

    @patch('digital_meal.portability.services.TikTokPortabilityAPIClient.poll_data_request_status')
    def test_download_await_view_with_request_status_downloading(self, mock_poll_response):
        mock_data = self.mock_poll_data.copy()
        mock_data['data']['status'] = 'downloading'
        mock_poll_response.return_value = mock_data

        data_request = self.create_data_request_in_db()
        _ = self.view.get_context_data()
        data_request.refresh_from_db()

        self.assertEqual(self.view.template_name, self.view.template_success)
        self.assertEqual(data_request.status, 'downloading')

    @patch('digital_meal.portability.services.TikTokPortabilityAPIClient.poll_data_request_status')
    def test_download_await_view_with_request_status_expired(self, mock_poll_response):
        mock_data = self.mock_poll_data.copy()
        mock_data['data']['status'] = 'expired'
        mock_poll_response.return_value = mock_data

        data_request = self.create_data_request_in_db()
        _ = self.view.get_context_data()
        data_request.refresh_from_db()

        self.assertEqual(self.view.template_name, self.view.template_expired)
        self.assertEqual(data_request.status, 'expired')


class TestTikTokDisconnectView(TestCase):

    def setUp(self):
        self.open_id = 'test-open-id'

        # Initialize session and store open id
        self.request = get_request_with_session()
        self.request.session[ManageAccessTokenMixin.open_id_session_key] = self.open_id
        self.request.session.save()

    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_view_deletes_open_id_in_session(self, mock_redirect):
        mock_redirect.return_value = HttpResponse()

        self.client.get('/')

        session = self.client.session
        session[ManageAccessTokenMixin.open_id_session_key] = self.open_id
        session.save()

        url = reverse('tiktok_disconnect')
        self.client.get(url)

        self.assertNotIn(
            ManageAccessTokenMixin.open_id_session_key,
            self.client.session.keys()
        )
        mock_redirect.assert_called_once()


    @patch('digital_meal.portability.views.redirect_to_auth_view')
    def test_view_when_open_id_not_in_session(self, mock_redirect):
        mock_redirect.return_value = HttpResponse()

        url = reverse('tiktok_disconnect')
        self.client.get(url)

        self.assertNotIn(
            ManageAccessTokenMixin.open_id_session_key,
            self.client.session.keys()
        )
        mock_redirect.assert_called_once()
