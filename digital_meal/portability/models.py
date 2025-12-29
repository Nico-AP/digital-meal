import logging
import requests

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from encrypted_fields import EncryptedTextField

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
        """ Remove old tokens (both used and unused). """
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

    def refresh(self) -> str | None:
        """Refreshes the access token through the TikTok user access token API.

        Raises:
            requests.exceptions.RequestException: If refresh request receives
                invalid response.

        Returns:
            str | None: Refreshed token or None if refresh fails.
        """
        if self.refresh_token_expiration_date < timezone.now():
            logger.info(
                'Refresh token is expire for TikTokAccessToken %s (expiration date: %s)',
                self.pk, self.refresh_token_expiration_date
            )
            return None

        url = settings.TIKTOK_TOKEN_URL
        data = {
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }
        headers = {'Accept': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning(
                'Unable to refresh TikTokAccessToken %s: %s', self.pk, e
            )
            return None

        data = response.json()

        # Update token values.
        self.token = data['access_token']
        self.token_expiration_date = timezone.now() + timedelta(seconds=data['expires_in'])
        self.refresh_token = data['refresh_token']
        self.refresh_token_expiration_date = timezone.now() + timedelta(seconds=data['refresh_expires_in'])
        self.token_type = data['token_type']
        self.scope = data['scope']
        self.save()
        return self.token

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
