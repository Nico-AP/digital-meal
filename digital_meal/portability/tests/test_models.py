import time
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from digital_meal.portability.models import (
    OAuthStateToken,
    TikTokAccessToken,
    TikTokDataRequest
)


class TestOAuthStateToken(TestCase):

    def test_save_generates_token(self):
        token = OAuthStateToken.objects.create()
        self.assertEqual(len(token.token), 50)
        self.assertIsInstance(token.token, str)

    def test_is_expired_for_expired_token(self):
        expired_token = OAuthStateToken.objects.create()
        expired_token.created_at = timezone.now() - timedelta(minutes=11)
        self.assertTrue(expired_token.is_expired())

    def test_is_expired_for_active_token(self):
        active_token = OAuthStateToken.objects.create()
        self.assertFalse(active_token.is_expired())

    def test_cleanup_expired_deletes_old_tokens(self):
        expired_token = OAuthStateToken.objects.create()
        expired_token.created_at = timezone.now() - timedelta(hours=24)
        expired_token.save()
        active_token = OAuthStateToken.objects.create()

        self.assertEqual(OAuthStateToken.objects.count(), 2)
        time.sleep(2)
        n_deleted = OAuthStateToken.cleanup_expired()

        self.assertEqual(n_deleted, 1)
        self.assertEqual(OAuthStateToken.objects.count(), 1)

    def test_cleanup_expired_no_objects(self):
        n_deleted = OAuthStateToken.cleanup_expired()
        self.assertEqual(n_deleted, 0)


class TestTikTokAccessToken(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.token = TikTokAccessToken.objects.create(
            open_id='test-id',
            token='test-token',
            token_expiration_date=timezone.now(),
            refresh_token='test-token',
            refresh_token_expiration_date=timezone.now(),
            scope='test-scope-a,test-scope-b'
        )

    def test_is_expired_for_expired_token(self):
        self.token.token_expiration_date = timezone.now() - timedelta(hours=1)
        self.assertTrue(self.token.is_expired())

    def test_is_expired_for_active_token(self):
        self.token.token_expiration_date = timezone.now() + timedelta(hours=24)
        self.assertFalse(self.token.is_expired())

    def test_refresh_is_expired_for_expired_token(self):
        self.token.refresh_token_expiration_date = timezone.now() - timedelta(hours=1)
        self.assertTrue(self.token.refresh_is_expired())

    def test_refresh_is_expired_for_active_token(self):
        self.token.refresh_token_expiration_date = timezone.now() + timedelta(hours=24)
        self.assertFalse(self.token.refresh_is_expired())

    def test_get_scope_list(self):
        scope_list = self.token.get_scope_list()
        self.assertEqual(len(scope_list), 2)


class TestTikTokDataRequest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.data_request = TikTokDataRequest.objects.create(
            open_id='test-id',
            request_id=1234567890,
        )

    def test_is_active_for_inactive_request(self):
        self.data_request.status = 'expired'
        self.assertFalse(self.data_request.is_active())

    def test_is_active_for_downloaded_request(self):
        self.data_request.download_succeeded = True
        self.assertFalse(self.data_request.is_active())

    def test_is_active_for_active_request(self):
        self.assertTrue(self.data_request.is_active())
