from django.test import TestCase

from mydigitalmeal.statistics.models import (
    StatisticsRequest,
    StatisticsScope,
    TikTokWatchHistoryStatistics,
)


class TestStatisticsRequestModel(TestCase):
    def setUp(self):
        self.stats_request = StatisticsRequest.objects.create()

    def test_statistics_ready(self):
        self.assertFalse(self.stats_request.is_ready())
        self.stats_request.status = StatisticsRequest.States.SUCCESS
        self.assertTrue(self.stats_request.is_ready())

    def test_get_statistics(self):
        TikTokWatchHistoryStatistics.objects.create(
            request=self.stats_request, scope=StatisticsScope.FULL
        )
        TikTokWatchHistoryStatistics.objects.create(
            request=self.stats_request, scope=StatisticsScope.INTERVAL
        )
        statistics = self.stats_request.get_statistics()
        self.assertEqual(len(statistics), 2)

    def test_set_complete(self):
        self.stats_request.set_success()
        self.stats_request.refresh_from_db()
        self.assertEqual(self.stats_request.status, StatisticsRequest.States.SUCCESS)

    def test_set_complete_with_details(self):
        some_details = {"abc": 123}
        self.stats_request.set_success(str(some_details))
        self.stats_request.refresh_from_db()
        self.assertEqual(self.stats_request.status, StatisticsRequest.States.SUCCESS)
        self.assertEqual(self.stats_request.status_detail, str(some_details))

    def test_set_retrying(self):
        self.stats_request.set_retrying()
        self.stats_request.refresh_from_db()
        self.assertEqual(self.stats_request.status, StatisticsRequest.States.RETRY)

    def test_set_failed(self):
        self.stats_request.set_failed()
        self.stats_request.refresh_from_db()
        self.assertEqual(self.stats_request.status, StatisticsRequest.States.FAILED)


class TestTikTokWatchHistoryStatisticsModel(TestCase):
    pass
