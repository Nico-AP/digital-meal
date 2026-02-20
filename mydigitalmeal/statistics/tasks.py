import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from mydigitalmeal.statistics.models.base import StatisticsRequest, StatisticsScope
from mydigitalmeal.statistics.models.tiktok import TikTokWatchHistoryStatistics
from mydigitalmeal.statistics.services.tiktok_statistics import (
    WatchHistoryStatisticsGenerator,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def compute_tiktok_wh_statistics(
    self,
    watch_history_data: list[dict],
    statistics_scope: StatisticsScope = StatisticsScope.FULL,
    statistics_request_id: int | None = None,
) -> dict:
    """Compute TikTok watch history statistics asynchronously.

    Args:
        self: Celery task instance (bound task)
        watch_history_data: Raw watch history data from donation
        statistics_scope: Scope of the statistics request
        statistics_request_id: The ID of the statistics request object

    Returns:
        dict: Statistics computation result with status and stats_id
    """
    try:
        # Generate statistics
        stats_dict = WatchHistoryStatisticsGenerator(
            watch_history_data,
            scope=statistics_scope,
        ).generate_all()

        statistics_request = StatisticsRequest.objects.filter(
            pk=statistics_request_id
        ).first()

        # Create and save statistics record
        stats = TikTokWatchHistoryStatistics(
            request=statistics_request,
            **stats_dict,
        )
        stats.save()

        if statistics_request:
            statistics_request.set_success()
            request_id = statistics_request.public_id
        else:
            request_id = "No attached statistics request object"

        logger.info(
            "Successfully computed statistics for request %s. Stats ID: %s",
            statistics_request,
            stats.public_id,
        )

        return {
            "status": "success",
            "statistics_request_id": str(request_id),
            "stats_id": str(stats.public_id),
        }

    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Failed to compute statistics for request %s: %s", statistics_request_id, e
        )

        statistics_request = StatisticsRequest.objects.filter(
            pk=statistics_request_id
        ).first()

        if statistics_request:
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
