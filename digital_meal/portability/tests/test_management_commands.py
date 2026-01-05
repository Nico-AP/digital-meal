from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from digital_meal.portability.management.commands.clean_expired_tokens import (
    clean_oauth_tokens,
    clean_access_tokens
)
from digital_meal.portability.models import OAuthStateToken, TikTokAccessToken


class TestCleanOAuthTokensFunction(TestCase):
    """Tests for clean_oauth_tokens() function"""

    def test_deletes_used_tokens(self):
        """Test deletes tokens marked as used"""
        used_token = OAuthStateToken.objects.create(used=True)
        unused_token = OAuthStateToken.objects.create(used=False)

        clean_oauth_tokens()

        self.assertFalse(OAuthStateToken.objects.filter(pk=used_token.pk).exists())
        self.assertTrue(OAuthStateToken.objects.filter(pk=unused_token.pk).exists())

    def test_deletes_expired_tokens(self):
        """Test deletes tokens that are expired (older than 24 hours by default)"""
        expired_token = OAuthStateToken.objects.create(used=False)
        expired_token.created_at = timezone.now() - timedelta(hours=25)
        expired_token.save()
        recent_token = OAuthStateToken.objects.create(used=False)

        clean_oauth_tokens()

        self.assertFalse(OAuthStateToken.objects.filter(pk=expired_token.pk).exists())
        self.assertTrue(OAuthStateToken.objects.filter(pk=recent_token.pk).exists())

    def test_handles_no_tokens_to_delete(self):
        """Test handles case when there are no tokens to delete"""
        OAuthStateToken.objects.create(used=False)

        clean_oauth_tokens()


class TestCleanAccessTokensFunction(TestCase):
    """Tests for clean_access_tokens() function"""

    def test_deletes_tokens_with_expired_refresh_tokens(self):
        """Test deletes tokens where refresh token has expired"""
        expired_token = TikTokAccessToken.objects.create(
            open_id='expired_user',
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() - timedelta(days=1),
            scope='user.info.basic',
            token_type='Bearer'
        )

        valid_token = TikTokAccessToken.objects.create(
            open_id='valid_user',
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() + timedelta(days=30),
            scope='user.info.basic',
            token_type='Bearer'
        )

        clean_access_tokens()

        self.assertFalse(TikTokAccessToken.objects.filter(pk=expired_token.pk).exists())
        self.assertTrue(TikTokAccessToken.objects.filter(pk=valid_token.pk).exists())

    def test_does_not_delete_tokens_with_valid_refresh_tokens(self):
        """Test does not delete tokens with valid refresh tokens"""
        valid_token = TikTokAccessToken.objects.create(
            open_id='valid_user',
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() + timedelta(days=30),
            scope='user.info.basic',
            token_type='Bearer'
        )

        clean_access_tokens()

        self.assertTrue(TikTokAccessToken.objects.filter(pk=valid_token.pk).exists())

    def test_handles_no_tokens_to_delete(self):
        """Test handles case when there are no tokens to delete"""
        TikTokAccessToken.objects.create(
            open_id='valid_user',
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() + timedelta(days=30),
            scope='user.info.basic',
            token_type='Bearer'
        )

        clean_access_tokens()


class TestCleanExpiredTokensCommand(TestCase):
    """Tests for the clean_expired_tokens management command"""

    @patch('digital_meal.portability.management.commands.clean_expired_tokens.clean_access_tokens')
    @patch('digital_meal.portability.management.commands.clean_expired_tokens.clean_oauth_tokens')
    def test_command_calls_both_clean_functions(self, mock_clean_oauth, mock_clean_access):
        """Test command calls both clean_oauth_tokens and clean_access_tokens"""
        call_command('clean_expired_tokens')

        mock_clean_oauth.assert_called_once()
        mock_clean_access.assert_called_once()

    def test_command_executes_without_error(self):
        """Test command can be executed without errors"""
        OAuthStateToken.objects.create(used=True)
        TikTokAccessToken.objects.create(
            open_id='user',
            token='token',
            token_expiration_date=timezone.now() - timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() - timedelta(days=1),
            scope='user.info.basic',
            token_type='Bearer'
        )

        call_command('clean_expired_tokens', stdout=StringIO())

    def test_command_integration_deletes_tokens(self):
        """Integration test: command actually deletes the right tokens"""
        used_oauth = OAuthStateToken.objects.create(used=True)
        unused_oauth = OAuthStateToken.objects.create(used=False)

        expired_access = TikTokAccessToken.objects.create(
            open_id='expired_user',
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() - timedelta(days=1),
            scope='user.info.basic',
            token_type='Bearer'
        )

        valid_access = TikTokAccessToken.objects.create(
            open_id='valid_user',
            token='token',
            token_expiration_date=timezone.now() + timedelta(hours=1),
            refresh_token='refresh',
            refresh_token_expiration_date=timezone.now() + timedelta(days=30),
            scope='user.info.basic',
            token_type='Bearer'
        )

        call_command('clean_expired_tokens')

        self.assertFalse(OAuthStateToken.objects.filter(pk=used_oauth.pk).exists())
        self.assertTrue(OAuthStateToken.objects.filter(pk=unused_oauth.pk).exists())
        self.assertFalse(TikTokAccessToken.objects.filter(pk=expired_access.pk).exists())
        self.assertTrue(TikTokAccessToken.objects.filter(pk=valid_access.pk).exists())
