from unittest.mock import patch

from django.db import connection
from django.test import TestCase

from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.statistics.tasks import compute_tiktok_wh_statistics_from_donation


def _corrupt_public_id(pk: int) -> None:
    """Writes a non-UUID string directly into `public_id` via raw SQL.

    Django's UUIDField coerces/validates the value on every ORM write path
    (`.create()`, `.save()`, even `.update()`), so there is no way to
    reproduce the corrupted value observed in production through the ORM -
    whatever wrote it there must have gone around Django entirely (raw SQL,
    a data import/restore, etc.). Raw SQL is therefore also the only way to
    simulate it here.
    """
    table = StatisticsRequest._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} SET public_id = %s WHERE id = %s",  # noqa: S608
            ["not-a-valid-uuid", pk],
        )


class TestComputeTiktokWhStatisticsFromDonation(TestCase):
    """Regression tests for a production incident: a corrupted ``public_id``
    value on a ``StatisticsRequest`` row crashed this task with an
    unhandled ``ValueError`` ("badly formed hexadecimal UUID string") the
    moment the row was fetched - before any of the task's own logic ran.
    Because the crash happened outside the try/except, the request was
    never marked FAILED and stayed PENDING forever, which is also why the
    studies report could get stuck in an endless loading state (see
    ``mydigitalmeal.studies.views.StudyStatisticsView``).
    """

    def setUp(self):
        self.stats_request = StatisticsRequest.objects.create(
            status=StatisticsRequest.States.PENDING,
        )
        _corrupt_public_id(self.stats_request.pk)

    @patch("mydigitalmeal.statistics.tasks.get_tiktok_wh_data")
    def test_does_not_crash_on_corrupted_public_id(self, mock_get_data):
        mock_get_data.return_value = []

        result = compute_tiktok_wh_statistics_from_donation(
            statistics_scope=StatisticsScope.INTERVAL,
            statistics_request_id=self.stats_request.pk,
        )

        self.assertEqual(result["status"], "success")

        # Avoid `refresh_from_db()` / any full-row fetch here - it would
        # reload `public_id` too and hit the exact same crash, this time
        # in the test's own assertions.
        updated = StatisticsRequest.objects.defer("public_id").get(
            pk=self.stats_request.pk
        )
        self.assertEqual(updated.status, StatisticsRequest.States.FAILED)
        self.assertEqual(updated.status_detail, "No data in watch history")
