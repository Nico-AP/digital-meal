import logging
import requests

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from encrypted_fields import EncryptedTextField

from digital_meal.portability.exceptions import TokenRefreshException

logger = logging.getLogger(__name__)


class OAuthToken(models.Model):
    """Class to store state tokens used for OAuth."""
    token = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # On create, generate token
        if not self.pk and not self.token:
            new_token = get_random_string(50)
            while OAuthToken.objects.filter(token=new_token).exists():
                new_token = get_random_string(50)
            self.token = new_token

        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        """Checks whether the Token is still valid.

        Tokens are valid for 10 minutes.

        Returns:
            bool: True if still active, False otherwise.
        """
        cutoff = timezone.now() - timedelta(minutes=10)
        return self.created_at < cutoff

    @classmethod
    def cleanup_expired(cls, hours: int = 24) -> int:
        """Remove old tokens (both used and unused)."""
        cutoff = timezone.now() - timedelta(hours=hours)
        deleted_count = cls.objects.filter(created_at__lt=cutoff).delete()[0]
        return deleted_count


class TikTokAccessToken(models.Model):
    open_id = models.CharField(
        max_length=250,
        unique=True,
        verbose_name='ID of TikTok user'
    )

    token = EncryptedTextField(max_length=250)
    token_expiration_date = models.DateTimeField(null=True)

    refresh_token = EncryptedTextField(max_length=250)
    refresh_token_expiration_date = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    scope = models.CharField(max_length=250) # Comma separated list of scopes

    token_type = models.CharField(max_length=50)

    def is_expired(self, threshold: int = 0) -> bool:
        """Check if token is expired or expiring soon.

        Args:
            threshold: Time in seconds before actual expiration to consider
                token expired.

        Returns:
            bool: True if token is expired (or expiring soon)
        """
        expiration_time = self.token_expiration_date - timedelta(seconds=threshold)
        return timezone.now() > expiration_time

    def refresh_is_expired(self, threshold: int = 0) -> bool:
        """Check if refresh token is expired or expiring soon.

        Args:
            threshold: Time in seconds before actual expiration to consider
                token expired.

        Returns:
            bool: True if token is expired (or expiring soon)
        """
        expiration_time = self.refresh_token_expiration_date - timedelta(seconds=threshold)
        return timezone.now() > expiration_time

    def get_scope_list(self) -> list:
        return self.scope.split(',')


class TikTokDataRequest(models.Model):
    open_id = models.CharField(
        max_length=250,
        verbose_name='ID of TikTok user'
    )
    request_id = models.BigIntegerField(
        unique=True,
        verbose_name='ID of data request'
    )
    issued_at = models.DateTimeField(default=timezone.now)

    last_polled = models.DateTimeField(null=True)

    status = models.CharField(
        max_length=20,
        default='not-polled',
    )

    download_attempted = models.BooleanField(default=False)
    download_succeeded = models.BooleanField(default=False)
    downloaded_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-issued_at']

    def active(self) -> bool:
        inactive_states = ['expired', 'cancelled']
        if self.status in inactive_states or self.download_succeeded:
            return False

        return True
