from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from mydigitalmeal.statistics.models import TikTokWatchHistoryStatistics


class BaseModelStatistics(models.Model):
    public_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True


class StatisticsScope(models.TextChoices):
    FULL = "FULL", "Full History"
    INTERVAL = "INTERVAL", "Date range"


class StatisticsRequest(models.Model):
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
    )

    profile = models.ForeignKey(
        "mydigitalmeal_profiles.MDMProfile",
        on_delete=models.SET_NULL,
        null=True,
        related_name="statistics_requests",
    )

    participant = models.ForeignKey(
        "ddm_participation.Participant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="statistics_requests",
    )

    requested_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class States(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RETRY = "RETRY", "Retry"
        FAILED = "FAILED", "Failed"
        SUCCESS = "SUCCESS", "Success"

    status = models.CharField(
        choices=States.choices,
        max_length=20,
        default=States.PENDING,
    )

    status_detail = models.TextField()

    class Meta:
        verbose_name = "Statistics Request"
        verbose_name_plural = "Statistics Requests"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Statistics request {self.public_id}"

    def is_ready(self) -> bool:
        return self.status in [self.States.SUCCESS, self.States.FAILED]

    def has_failed(self):
        return self.status == self.States.FAILED

    def get_statistics(self) -> QuerySet[TikTokWatchHistoryStatistics]:
        return self.tiktok_wh_statistics.all()

    def set_success(self, status_detail: str | None = None):
        self.status = self.States.SUCCESS
        if status_detail:
            self.status_detail = status_detail
        self.save()

    def set_retrying(self, status_detail: str | None = None):
        self.status = self.States.RETRY
        if status_detail:
            self.status_detail = status_detail
        self.save()

    def set_failed(self, status_detail: str | None = None):
        self.status = self.States.FAILED
        if status_detail:
            self.status_detail = status_detail
        self.save()
