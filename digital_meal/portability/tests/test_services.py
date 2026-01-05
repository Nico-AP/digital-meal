from datetime import timedelta
from unittest.mock import patch, Mock

from django.http import StreamingHttpResponse
from django.test import TestCase
from django.utils import timezone
from requests import Timeout

from digital_meal.portability.exceptions import TokenRefreshException
from digital_meal.portability.models import TikTokAccessToken, TikTokDataRequest
from digital_meal.portability.services import (
    TikTokAccessTokenService,
    TikTokPortabilityAPIClient
)


class TestTikTokAccessTokenService(TestCase):
    """Tests for TikTokAccessTokenService"""

    def setUp(self):
        self.service = TikTokAccessTokenService()
        self.valid_token = TikTokAccessToken.objects.create(
            open_id='test_123',
            token='valid_token',
            token_expiration_date=timezone.now() + timedelta(hours=5),
            refresh_token='valid_refresh_token',
            refresh_token_expiration_date=timezone.now() + timedelta(days=30),
            scope='user.info.basic,portability.all.single',
            token_type='Bearer'
        )

    # ===== refresh_token() Tests =====

    @patch('digital_meal.portability.services.TikTokAccessTokenService._call_tiktok_api')
    def test_refresh_token_success(self, mock_post):
        mock_post.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600,
            'refresh_token': 'new_refresh_token',
            'refresh_expires_in': 2592000,
            'token_type': 'Bearer',
            'scope': 'user.info.basic,portability.all.single'
        }

        refreshed_token = self.service.refresh_token(self.valid_token)

        self.assertEqual(refreshed_token.token, 'new_access_token')
        self.assertEqual(refreshed_token.refresh_token, 'new_refresh_token')
        self.assertFalse(refreshed_token.is_expired())
        mock_post.assert_called_once()

    def test_refresh_token_when_refresh_token_expired(self):
        """Test refresh fails when refresh token is expired"""
        expired_token = TikTokAccessToken.objects.create(
            open_id='test_expired',
            token='expired_token',
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token='expired_refresh_token',
            refresh_token_expiration_date=timezone.now() - timedelta(days=1),
            scope='user.info.basic',
            token_type='Bearer'
        )

        with self.assertRaises(TokenRefreshException) as e:
            self.service.refresh_token(expired_token)

    @patch('digital_meal.portability.services.TikTokAccessTokenService._call_tiktok_api')
    def test_refresh_token_updates_all_fields(self, mock_post):
        """Test that refresh updates all token fields correctly"""
        mock_post.return_value = {
            'access_token': 'updated_token',
            'expires_in': 7200,
            'refresh_token': 'updated_refresh',
            'refresh_expires_in': 5184000,
            'token_type': 'Bearer',
            'scope': 'user.info.basic'
        }

        old_token_value = self.valid_token.token
        _ = self.service.refresh_token(self.valid_token)
        self.valid_token.refresh_from_db()

        self.assertNotEqual(self.valid_token.token, old_token_value)
        self.assertEqual(self.valid_token.token, 'updated_token')
        self.assertEqual(self.valid_token.token_type, 'Bearer')
        self.assertEqual(self.valid_token.scope, 'user.info.basic')

    # ===== check_token_data_is_valid() Tests =====

    def test_check_token_data_is_valid_with_valid_data(self):
        valid_data = {
            'access_token': 'token123',
            'expires_in': 3600,
            'open_id': 'test_id',
            'refresh_expires_in': 2592000,
            'refresh_token': 'refresh123',
            'scope': 'user.info.basic',
            'token_type': 'Bearer'
        }

        result = self.service.check_token_data_is_valid(valid_data)

        self.assertTrue(result)

    def test_check_token_data_is_valid_with_missing_field(self):
        """Test validation fails when required field is missing"""
        invalid_data = {
            'access_token': 'token123',
            'expires_in': 3600,
            # Missing 'open_id'
            'refresh_expires_in': 2592000,
            'refresh_token': 'refresh123',
            'scope': 'user.info.basic',
            'token_type': 'Bearer'
        }

        result = self.service.check_token_data_is_valid(invalid_data)

        self.assertFalse(result)

    def test_check_token_data_is_valid_with_non_dict(self):
        """Test validation fails when data is not a dictionary"""
        result = self.service.check_token_data_is_valid("not a dict")
        self.assertFalse(result)

    def test_check_token_data_is_valid_with_none(self):
        """Test validation fails with None"""
        result = self.service.check_token_data_is_valid(None)
        self.assertFalse(result)

    # ===== update_or_create_access_token() Tests =====

    def test_update_or_create_creates_new_token(self):
        """Test creates new token when none exists for open_id"""
        token_data = {
            'access_token': 'new_token',
            'expires_in': 3600,
            'open_id': 'new_user_456',
            'refresh_expires_in': 2592000,
            'refresh_token': 'new_refresh',
            'scope': 'user.info.basic',
            'token_type': 'Bearer'
        }

        token = self.service.update_or_create_access_token(token_data)

        self.assertIsNotNone(token.pk)
        self.assertEqual(token.open_id, 'new_user_456')
        self.assertEqual(token.token, 'new_token')
        self.assertEqual(TikTokAccessToken.objects.filter(open_id='new_user_456').count(), 1)

    def test_update_or_create_updates_existing_token(self):
        """Test updates existing token for same open_id"""
        existing = TikTokAccessToken.objects.create(
            open_id='test_id',
            token='old_token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='old_refresh',
            refresh_token_expiration_date=timezone.now() + timedelta(days=30),
            scope='old_scope',
            token_type='Bearer'
        )

        token_data = {
            'access_token': 'updated_token',
            'expires_in': 7200,
            'open_id': 'test_id',
            'refresh_expires_in': 5184000,
            'refresh_token': 'updated_refresh',
            'scope': 'new_scope',
            'token_type': 'Bearer'
        }

        token = self.service.update_or_create_access_token(token_data)

        self.assertEqual(token.pk, existing.pk)
        self.assertEqual(token.token, 'updated_token')
        self.assertEqual(token.scope, 'new_scope')
        self.assertEqual(TikTokAccessToken.objects.filter(open_id='test_id').count(), 1)

    # ===== exchange_code_for_token() Tests =====

    @patch('digital_meal.portability.services.requests.post')
    def test_exchange_code_for_token_success(self, mock_post):
        """Test successful code exchange"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'exchanged_token',
            'expires_in': 3600,
            'open_id': 'user_789',
            'refresh_expires_in': 2592000,
            'refresh_token': 'exchanged_refresh',
            'scope': 'user.info.basic',
            'token_type': 'Bearer'
        }
        mock_post.return_value = mock_response

        result = self.service.exchange_code_for_token('test_auth_code')

        self.assertEqual(result['access_token'], 'exchanged_token')
        self.assertEqual(result['open_id'], 'user_789')
        mock_post.assert_called_once()

    @patch('digital_meal.portability.services.requests.post')
    @patch('digital_meal.portability.services.time.sleep')
    def test_exchange_code_for_token_retries_on_timeout(self, mock_sleep, mock_post):
        """Test retry logic on timeout"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'token'}

        # First call times out, second succeeds
        mock_post.side_effect = [Timeout(), mock_response]
        result = self.service.exchange_code_for_token('auth_code_123')

        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(3)
        self.assertIsNotNone(result)

    @patch('digital_meal.portability.services.requests.post')
    @patch('digital_meal.portability.services.time.sleep')
    def test_exchange_code_for_token_gives_up_after_max_attempts(self, mock_sleep, mock_post):
        """Test stops retrying after max attempts"""
        mock_post.side_effect = Timeout()

        with self.assertRaises(Exception):
            self.service.exchange_code_for_token('auth_code_123')

        # Should try 3 times (initial + 2 retries)
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)


class TestTikTokPortabilityAPIClient(TestCase):
    """Tests for TikTokPortabilityAPIClient"""

    def setUp(self):
        self.api_client = TikTokPortabilityAPIClient(access_token='test_token')
        self.test_data_request = TikTokDataRequest.objects.create(
            open_id='test_user',
            request_id=12345,
            status='pending'
        )

    # ===== make_data_request() Tests =====

    @patch('digital_meal.portability.services.requests.post')
    def test_make_data_request_success(self, mock_post):
        """Test successful data request creation"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {'code': 'ok'},
            'data': {'request_id': 98765}
        }
        mock_post.return_value = mock_response

        result = self.api_client.make_data_request()

        self.assertEqual(result['data']['request_id'], 98765)
        self.assertEqual(result['error']['code'], 'ok')

    # ===== data_request_response_is_valid() Tests =====

    def test_data_request_response_is_valid_when_ok_and_request_id_present(self):
        """Test validation passes with valid response"""
        valid_response = {
            'error': {'code': 'ok'},
            'data': {'request_id': 12345}
        }

        is_valid, message = self.api_client.data_request_response_is_valid(valid_response)

        self.assertTrue(is_valid)
        self.assertEqual(message, 'ok')

    def test_data_request_response_is_valid_when_error_code_not_ok(self):
        """Test validation fails when error code is not 'ok'"""
        invalid_response = {
            'error': {
                'code': 'invalid_token',
                'message': 'Token is invalid'
            }
        }

        is_valid, message = self.api_client.data_request_response_is_valid(invalid_response)

        self.assertFalse(is_valid)
        self.assertIn('invalid_token', message)

    def test_data_request_response_is_valid_when_request_id_missing(self):
        """Test validation fails when request_id is missing"""
        invalid_response = {
            'error': {'code': 'ok'},
            'data': {}
        }

        is_valid, message = self.api_client.data_request_response_is_valid(invalid_response)

        self.assertFalse(is_valid)
        self.assertIn('request_id', message)

    def test_data_request_response_is_valid_with_missing_data_key(self):
        """Test validation fails when 'data' key is missing"""
        invalid_response = {
            'error': {'code': 'ok'}
            # Missing 'data' key entirely
        }

        is_valid, message = self.api_client.data_request_response_is_valid(invalid_response)

        self.assertFalse(is_valid)

    # ===== poll_data_request_status() Tests =====

    @patch('digital_meal.portability.services.requests.post')
    def test_poll_status_success(self, mock_post):
        """Test successful status polling"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {'code': 'ok'},
            'data': {
                'request_id': 12345,
                'status': 'downloading',
                'apply_time': '2025-01-01T00:00:00Z',
                'collect_time': '2025-01-01T01:00:00Z'
            }
        }
        mock_post.return_value = mock_response

        result = self.api_client.poll_data_request_status(12345)

        self.assertEqual(result['data']['status'], 'downloading')
        self.assertEqual(result['data']['request_id'], 12345)

    @patch('digital_meal.portability.services.requests.post')
    def test_poll_status_timeout(self, mock_post):
        """Test returns error dict on timeout"""
        mock_post.side_effect = Timeout()

        result = self.api_client.poll_data_request_status(12345)

        self.assertIn('error', result)
        self.assertIn('timed out', result['error'])

    # ===== poll_data_request_status_response_is_valid() Tests =====

    def test_poll_status_response_is_valid_when_ok_and_valid_status(self):
        """Test validation passes with valid status response"""
        valid_response = {
            'error': {'code': 'ok'},
            'data': {
                'request_id': 12345,
                'status': 'pending'
            }
        }

        is_valid, message = self.api_client.poll_data_request_status_response_is_valid(valid_response)

        self.assertTrue(is_valid)
        self.assertEqual(message, 'ok')

    def test_poll_status_response_is_valid_when_error_code_not_ok(self):
        """Test validation fails when error code is not 'ok'"""
        invalid_response = {
            'error': {
                'code': 'not_found',
                'message': 'Request not found'
            }
        }

        is_valid, message = self.api_client.poll_data_request_status_response_is_valid(invalid_response)

        self.assertFalse(is_valid)
        self.assertIn('invalid error code', message)

    def test_poll_status_response_is_valid_when_data_missing(self):
        """Test validation fails when 'data' is missing"""
        invalid_response = {
            'error': {'code': 'ok'}
            # Missing 'data'
        }

        is_valid, message = self.api_client.poll_data_request_status_response_is_valid(invalid_response)

        self.assertFalse(is_valid)
        self.assertIn('Missing "data"', message)

    def test_poll_status_response_is_valid_when_status_code_invalid(self):
        """Test validation fails with invalid status code"""
        invalid_response = {
            'error': {'code': 'ok'},
            'data': {
                'request_id': 12345,
                'status': 'unknown_status'
            }
        }

        is_valid, message = self.api_client.poll_data_request_status_response_is_valid(invalid_response)

        self.assertFalse(is_valid)
        self.assertIn('Invalid status code', message)

    def test_poll_status_response_is_valid_accepts_all_valid_statuses(self):
        """Test validation accepts all valid status codes"""
        valid_statuses = ['pending', 'downloading', 'expired', 'cancelled']

        for status in valid_statuses:
            response = {
                'error': {'code': 'ok'},
                'data': {'status': status}
            }

            is_valid, message = self.api_client.poll_data_request_status_response_is_valid(response)

            self.assertTrue(is_valid, f"Status '{status}' should be valid")

    # ===== stream_download_requested_data() Tests =====

    @patch('digital_meal.portability.services.requests.post')
    def test_stream_download_returns_streaming_response(self, mock_post):
        """Test returns StreamingHttpResponse"""
        mock_response = Mock()
        mock_response.iter_content.return_value = iter([b'chunk1', b'chunk2'])
        mock_post.return_value = mock_response

        result = self.api_client.stream_download_requested_data(self.test_data_request)

        self.assertIsInstance(result, StreamingHttpResponse)

    @patch('digital_meal.portability.services.requests.post')
    def test_stream_download_updates_db_on_success(self, mock_post):
        """Test updates TikTokDataRequest on successful download"""
        mock_response = Mock()
        mock_response.iter_content.return_value = iter([b'data'])
        mock_post.return_value = mock_response

        result = self.api_client.stream_download_requested_data(self.test_data_request)
        # Consume the streaming response to trigger the cleanup
        list(result.streaming_content)

        self.test_data_request.refresh_from_db()
        self.assertTrue(self.test_data_request.download_succeeded)
        self.assertTrue(self.test_data_request.download_attempted)
        self.assertIsNotNone(self.test_data_request.downloaded_at)

    @patch('digital_meal.portability.services.requests.post')
    def test_stream_download_marks_failure_on_error(self, mock_post):
        """Test marks download as failed when error occurs during streaming"""
        def failing_iter():
            yield b'chunk1'
            raise Exception('Streaming error')

        mock_response = Mock()
        mock_response.iter_content.return_value = failing_iter()
        mock_post.return_value = mock_response

        result = self.api_client.stream_download_requested_data(self.test_data_request)
        with self.assertRaises(Exception):
            list(result.streaming_content)

        self.test_data_request.refresh_from_db()
        self.assertFalse(self.test_data_request.download_succeeded)
        self.assertTrue(self.test_data_request.download_attempted)
