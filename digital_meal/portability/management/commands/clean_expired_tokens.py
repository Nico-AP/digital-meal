import logging

from django.core.management import BaseCommand
from django.utils import timezone

from digital_meal.portability.models import OAuthStateToken, TikTokAccessToken

logger = logging.getLogger(__name__)


def clean_oauth_tokens() -> None:
    """Clean used and expired OAuthStateTokens.

    Logs the deletion counts of used and expired tokens.

    Returns:
        None
    """
    tokens_to_delete = OAuthStateToken.objects.filter(used=True)
    deleted_used_count = tokens_to_delete.delete()[0]

    deleted_expired_count = OAuthStateToken.cleanup_expired()

    logger.info(
        'Deleted %s used OAuth state tokens and %s expired OAuth tokens',
        deleted_used_count, deleted_expired_count
    )
    return


def clean_access_tokens() -> None:
    """Clean TikTokAccessTokens with expired refresh tokens.

    Logs the delection counts deleted tokens.

    Returns:
        None
    """
    tokens_to_delete = TikTokAccessToken.objects.filter(
        refresh_token_expiration_date__lt=timezone.now()
    )
    deleted_count = tokens_to_delete.delete()[0]

    logger.info(
        'Deleted %s access tokens with expired refresh tokens',
        deleted_count
    )
    return


class Command(BaseCommand):
    help = (
        'Deletes expired OAuthStateTokens and TikTokAccessTokens with expired '
        'refresh tokens.'
    )

    def handle(self, *args, **options):
        clean_oauth_tokens()
        clean_access_tokens()
