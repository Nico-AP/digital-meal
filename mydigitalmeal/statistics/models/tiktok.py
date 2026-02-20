from django.core.validators import MaxValueValidator
from django.db import models

from mydigitalmeal.statistics.models.base import BaseModelStatistics, StatisticsScope


class TikTokWatchHistoryStatistics(BaseModelStatistics):
    """Statistical summary of TikTok watch history data.

    This model stores pre-computed statistics derived from a participant's
    TikTok watch history. Statistics can be computed either on the full
    dataset or on a specific date interval.

    The statistics include:
    - Video viewing patterns (total videos, daily averages, peak activity
        times)
    - Session-based metrics (average session duration, videos per session)
    - Most watched content (top video and view count)
    - Activity distribution (active days, peak hours)

    Example:
        >>> generator = WatchHistoryStatisticsGenerator(
        ...     watch_history=raw_data,
        ...     scope=StatisticsScope.INTERVAL,
        ...     interval_start=start_date,
        ...     interval_end=end_date
        ... )
        >>> stats = TikTokWatchHistoryStatistics(
        ...     ddm_participant=participant,
        ...     profile=mdm_profile,
        ...     **generator.generate_all()
        ... )
        >>> stats.save()
    """

    request = models.ForeignKey(
        "mydigitalmeal_statistics.StatisticsRequest",
        on_delete=models.SET_NULL,
        null=True,
        related_name="tiktok_wh_statistics",
    )

    scope = models.CharField(
        choices=StatisticsScope.choices,
        max_length=20,
        help_text=(
            "Indicates whether statistics are computed on full dataset or on "
            "data in a specific interval."
        ),
    )

    # Interval bounds (only if scope == "INTERVAL")
    interval_start = models.DateTimeField(null=True, blank=True)
    interval_end = models.DateTimeField(null=True, blank=True)

    # Dataset bounds
    date_first_video = models.DateTimeField(null=True, blank=True)
    date_last_video = models.DateTimeField(null=True, blank=True)

    # Video counts
    total_videos = models.IntegerField(null=True, blank=True)
    total_videos_unique = models.IntegerField(null=True, blank=True)
    videos_per_day = models.FloatField(null=True, blank=True)
    total_days_with_activity = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of days on which some watch activity was recorded",
    )

    # Scrolling behaviour
    scroll_threshold_pct = models.FloatField(null=True, blank=True)
    scroll_threshold_sec = models.FloatField(null=True, blank=True)

    # Peak activity (most videos watched)
    peak_day_date = models.DateField(null=True, blank=True)
    peak_day_video_count = models.PositiveIntegerField(null=True, blank=True)
    peak_hour = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(23)],
        help_text="Hour of day (0-23) with most video views",
    )

    # Session-based statistics (i.e., based on "watch sequences")
    session_threshold_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Seconds of inactivity that define session boundaries",
    )

    avg_session_duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Mean session duration in seconds",
    )

    avg_videos_per_session = models.FloatField(null=True, blank=True)
    avg_seconds_per_video = models.FloatField(null=True, blank=True)

    # Most watched video
    top_video_id = models.CharField(
        default="",
        blank=True,
        max_length=25,  # usually 19 chars long, but we can't be totally sure.
    )
    top_video_seen_count = models.PositiveIntegerField(null=True, blank=True)
    top_video_last_seen_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "TikTok Watch History Statistics"
        verbose_name_plural = "TikTok Watch History Statistics"
        ordering = ["-date_created"]

    def __str__(self):
        return f"TikTok Watch History Statistics {self.public_id} ({self.scope})"

    @property
    def interval_length(self):
        if self.interval_start is None or self.interval_end is None:
            return None

        delta = self.interval_end - self.interval_start
        return delta.days + 1
