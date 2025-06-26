import logging
import requests

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


logger = logging.getLogger(__name__)


class OAuthToken(models.Model):
    """
    Class to store state tokens used for OAuth.
    """
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
        """
        Checks whether the Token is still valid. Tokens are valid for 10 minutes.

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
    token = models.CharField(max_length=250)
    token_expiration_date = models.DateTimeField(null=True)

    refresh_token = models.CharField(max_length=250)
    refresh_token_expiration_date = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    open_id = models.CharField(
        max_length=250,
        unique=True,
        verbose_name='ID of TikTok user'
    )
    scope = models.CharField(max_length=250) # Comma separated list of scopes

    token_type = models.CharField(max_length=50)

    def refresh(self) -> str | None:
        """
        Refreshes the access token through the TikTok user access token API.
        Returns the refreshed token if successful or None if refresh fails.

        Returns:
            str | None: Refreshed token or None
        """
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
            msg = f'Unable to refresh TikTokAccessToken with pk "{self.pk}".'
            logger.info(msg)
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

    def is_expired(self) -> bool:
        return timezone.now() > self.token_expiration_date

    def get_scope_list(self):
        return self.scope.split(',')
