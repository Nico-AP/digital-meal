import logging
from unittest.mock import Mock
import requests
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory

from digital_meal.core.logging_utils import log_requests_exception, log_security_event


class TestLogSecurityEvent(TestCase):

    def setUp(self):
        self.logger = Mock(spec=logging.Logger)
        self.factory = RequestFactory()

    def _add_session_to_request(self, request):
        """Helper to add session to request"""
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_logs_basic_security_event(self):
        """Test logging a basic security event"""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request = self._add_session_to_request(request)

        log_security_event(
            self.logger,
            'Suspicious activity detected',
            request
        )

        self.logger.log.assert_called_once()

        call_args = self.logger.log.call_args
        self.assertEqual(call_args[0][0], logging.WARNING)  # Default level
        self.assertEqual(call_args[0][1], 'Suspicious activity detected')

        extra = call_args[1]['extra']
        self.assertEqual(extra['ip'], '192.168.1.100')
        self.assertEqual(extra['user_agent'], 'Mozilla/5.0')
        self.assertIsNotNone(extra['session_key'])

    def test_logs_with_custom_level(self):
        """Test logging with custom severity level"""
        request = self.factory.get('/admin/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        request = self._add_session_to_request(request)

        log_security_event(
            self.logger,
            'Failed login attempt',
            request,
            level=logging.ERROR
        )

        call_args = self.logger.log.call_args
        self.assertEqual(call_args[0][0], logging.ERROR)

    def test_logs_with_custom_extra_data(self):
        """Test logging with additional extra data"""
        request = self.factory.post('/api/data/')
        request.META['REMOTE_ADDR'] = '172.16.0.1'
        request = self._add_session_to_request(request)

        custom_extra = {
            'user_id': 'user_123',
            'attempted_action': 'delete_account',
            'resource_id': 'res_456'
        }

        log_security_event(
            self.logger,
            'Unauthorized access attempt',
            request,
            extra=custom_extra
        )

        extra = self.logger.log.call_args[1]['extra']
        self.assertEqual(extra['user_id'], 'user_123')
        self.assertEqual(extra['attempted_action'], 'delete_account')
        self.assertEqual(extra['resource_id'], 'res_456')
        self.assertEqual(extra['ip'], '172.16.0.1')

    def test_logs_without_session(self):
        """Test logging when request has no session"""
        request = self.factory.get('/public/')
        request.META['REMOTE_ADDR'] = '203.0.113.1'

        log_security_event(
            self.logger,
            'Security event',
            request
        )

        extra = self.logger.log.call_args[1]['extra']
        self.assertIsNone(extra['session_key'])
        self.assertEqual(extra['ip'], '203.0.113.1')

    def test_logs_with_missing_meta_fields(self):
        """Test logging when META fields are missing"""
        request = self.factory.get('/test/')
        request = self._add_session_to_request(request)

        log_security_event(
            self.logger,
            'Event with missing data',
            request
        )

        extra = self.logger.log.call_args[1]['extra']
        self.assertIsNone(extra['user_agent'])
        self.assertIsNotNone(extra['session_key'])

    def test_logs_with_proxy_headers(self):
        """Test logging with proxy forwarded IP"""
        request = self.factory.get('/api/')
        request.META['REMOTE_ADDR'] = '10.0.0.5'  # Proxy IP
        request.META['HTTP_X_FORWARDED_FOR'] = '198.51.100.1'
        request.META['HTTP_USER_AGENT'] = 'curl/7.68.0'
        request = self._add_session_to_request(request)

        log_security_event(
            self.logger,
            'Rate limit exceeded',
            request,
            extra={'forwarded_for': request.META.get('HTTP_X_FORWARDED_FOR')}
        )

        extra = self.logger.log.call_args[1]['extra']
        self.assertEqual(extra['ip'], '10.0.0.5')
        self.assertEqual(extra['forwarded_for'], '198.51.100.1')


class TestLogRequestsException(TestCase):

    def setUp(self):
        self.logger = Mock(spec=logging.Logger)
        self.url = 'https://api.example.com/data'

    def test_logs_with_basic_exception(self):
        """Test logging a basic requests exception"""
        e = requests.exceptions.RequestException('Connection failed')

        log_requests_exception(
            self.logger,
            self.url,
            e,
            'Failed to make request: %s',
            str(e)
        )

        self.logger.log.assert_called_once()

        call_args = self.logger.log.call_args
        self.assertEqual(call_args[0][0], logging.WARNING)  # Default level
        self.assertEqual(call_args[0][1], 'Failed to make request: %s')
        self.assertEqual(call_args[0][2], 'Connection failed')

        extra = call_args[1]['extra']
        self.assertEqual(extra['url'], self.url)
        self.assertEqual(extra['error_type'], 'RequestException')
        self.assertIsNone(extra['status_code'])

    def test_logs_http_error_with_response(self):
        """Test logging an HTTP error with response details"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found: Resource does not exist'

        e = requests.exceptions.HTTPError('404 Client Error')
        e.response = mock_response

        log_requests_exception(
            self.logger,
            self.url,
            e,
            'Request failed: %s',
            str(e),
            level=logging.ERROR
        )

        extra = self.logger.log.call_args[1]['extra']
        self.assertEqual(extra['status_code'], 404)
        self.assertEqual(extra['response_text'], 'Not Found: Resource does not exist')

    def test_logs_with_multiple_format_args(self):
        """Test logging with multiple format arguments"""
        e = requests.exceptions.Timeout('Request timed out')
        request_id = 123456

        log_requests_exception(
            self.logger,
            self.url,
            e,
            'Failed to poll data request status: %s (request_id: %s)',
            str(e),
            request_id,
            level=logging.ERROR
        )

        call_args = self.logger.log.call_args
        self.assertEqual(call_args[0][2], 'Request timed out')
        self.assertEqual(call_args[0][3], 123456)

    def test_logs_with_custom_extra_data(self):
        """Test logging with additional extra data"""
        e = requests.exceptions.RequestException('Error')
        custom_extra = {'user_id': 'user_789', 'retry_count': 3}

        log_requests_exception(
            self.logger,
            self.url,
            e,
            'Request failed: %s',
            str(e),
            extra=custom_extra
        )

        extra = self.logger.log.call_args[1]['extra']
        self.assertEqual(extra['user_id'], 'user_789')
        self.assertEqual(extra['retry_count'], 3)
        self.assertEqual(extra['url'], self.url)
