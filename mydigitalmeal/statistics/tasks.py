import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from ddm.datadonation.models import DataDonation

from mydigitalmeal.datadonation.utils import get_tiktok_wh_data
from mydigitalmeal.statistics.models.base import StatisticsRequest, StatisticsScope
from mydigitalmeal.statistics.models.tiktok import TikTokWatchHistoryStatistics
from mydigitalmeal.statistics.services.tiktok_statistics import (
    WatchHistoryStatisticsGenerator,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def compute_tiktok_wh_statistics_from_donation(
    self,
    statistics_scope: StatisticsScope = StatisticsScope.FULL,
    statistics_request_id: int | None = None,
) -> dict | None:
    """Compute TikTok watch history statistics asynchronously.

    Args:
        self: Celery task instance (bound task)
        statistics_scope: Scope of the statistics request
        statistics_request_id: The ID of the statistics request object

    Returns:
        dict: Statistics computation result with status and stats_id
    """
    statistics_request = StatisticsRequest.objects.filter(
        pk=statistics_request_id
    ).first()
    if not statistics_request:
        logger.error("StatisticsRequest %s not found, aborting.", statistics_request_id)
        return None

    participant = statistics_request.participant

    try:
        watch_history_data = get_tiktok_wh_data(participant)

        stats_dict = WatchHistoryStatisticsGenerator(
            watch_history_data,
            scope=statistics_scope,
        ).generate_all()

        stats = TikTokWatchHistoryStatistics(
            request=statistics_request,
            **stats_dict,
        )
        stats.save()
        statistics_request.set_success()

        logger.info(
            "Successfully computed statistics for request %s. Stats ID: %s",
            statistics_request,
            stats.public_id,
        )

        return {
            "status": "success",
            "statistics_request_id": str(statistics_request.public_id),
            "stats_id": str(stats.public_id),
        }

    except DataDonation.DoesNotExist as e:
        logger.warning("No donated data found for %s: %s", participant.external_id, e)
        statistics_request.set_failed()

    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Failed to compute statistics for request %s: %s", statistics_request_id, e
        )
        statistics_request.set_retrying()

        # Retry with exponential backoff
        try:
            raise self.retry(
                countdown=min(60 * (2**self.request.retries), 300),
                exc=e,
            ) from e
        except MaxRetriesExceededError as e:
            if statistics_request:
                statistics_request.set_failed()
            raise
