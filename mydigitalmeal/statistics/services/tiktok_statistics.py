import datetime
from typing import Any

import pandas as pd
from django.utils import timezone

import mydigitalmeal.statistics.utils.general.data as data_utils
from mydigitalmeal.statistics.models.base import StatisticsScope
from mydigitalmeal.statistics.utils.tiktok.data import load_tiktok_watch_history


class WatchHistoryStatisticsGenerator:
    """Generates statistical summaries from TikTok watch history data.

    This service class processes raw TikTok watch history data and computes
    various statistics including viewing patterns, session metrics, and
    peak activity times. The generated statistics can be used to populate a
    TikTokWatchHistoryStatistics model instance.

    The generator supports two analysis scopes:
    - FULL: Analyzes the entire watch history dataset
    - INTERVAL: Analyzes data within a specific date range (range defaults to
        last 30 days)

    Attributes:
        data (pd.DataFrame): Processed watch history data.
        stats (dict): Accumulated statistics dictionary.

    Example:
        >>> generator = WatchHistoryStatisticsGenerator(
        ...     watch_history=[
        ...         {"Date": "2024-01-15 10:00:00", "Link": "video123"},
        ...         {"Date": "2024-01-15 10:05:00", "Link": "video456"},
        ...     ],
        ...     scope=StatisticsScope.FULL
        ... )
        >>> stats = generator.generate_all()
        >>> print(stats['total_videos'])
        2
    """

    def __init__(
        self,
        watch_history: list[dict[str, Any]],
        scope: str,
        interval_start: datetime.datetime | None = None,
        interval_end: datetime.datetime | None = None,
        session_threshold_seconds: int = 600,  # 10 minutes default
    ) -> None:
        """
        Args:
            watch_history: Raw watch history data
            scope: StatisticsScope value (FULL or INTERVAL)
            interval_start: Start of interval (required if scope=INTERVAL)
            interval_end: End of interval (required if scope=INTERVAL)
            session_threshold_seconds: Seconds of inactivity defining session
                boundaries. Default is 1800 (30 minutes).
        """

        if not watch_history:
            msg = "watch_history cannot be empty"
            raise ValueError(msg)

        if scope not in [StatisticsScope.FULL, StatisticsScope.INTERVAL]:
            msg = f"Invalid scope: {scope}"
            raise ValueError(msg)

        if scope == StatisticsScope.INTERVAL:
            if not interval_start or not interval_end:
                interval_end = timezone.now()
                interval_start = interval_end - datetime.timedelta(days=30)
            if interval_start >= interval_end:
                msg = "interval_start must be before interval_end"
                raise ValueError(msg)

        self.raw_data = watch_history
        self.scope = scope
        self.interval_start = interval_start
        self.interval_end = interval_end
        self.session_threshold_seconds = session_threshold_seconds

        # Optional placeholders to pass statistics between functions
        self.durations_per_video: pd.Series | None = None

        self.data: pd.DataFrame = self._load_and_filter_data()
        self.stats: dict = {}

    def _load_and_filter_data(self) -> pd.DataFrame:
        """Load data and filter by interval if applicable."""

        data = load_tiktok_watch_history(self.raw_data)

        if self.scope == StatisticsScope.INTERVAL:
            data = data[
                (data["date"] <= self.interval_end)
                & (data["date"] >= self.interval_start)
            ]

        return data

    def generate_all(self) -> dict[str, Any]:
        """Adds all statistics to self.stats and returns them."""
        self.get_scope_fields()

        if self.data.empty:
            return self.stats

        self.get_dataset_bounds()
        self.compute_video_counts()
        self.compute_peak_activity()
        self.compute_session_statistics()
        self.compute_scrolling_statistics()
        self.get_top_video()
        return self.stats

    def get_scope_fields(self) -> dict[str, Any]:
        """Get scope and interval fields. Returns values and updates self.stats.

        Returns:
            dict: Dict includes "scope", and optionally "interval_start"
                and "interval_end
        """

        stats = {"scope": self.scope}

        if self.scope == StatisticsScope.INTERVAL:
            stats["interval_start"] = self.interval_start
            stats["interval_end"] = self.interval_end

        self.stats.update(stats)
        return stats

    def get_dataset_bounds(self) -> dict[str, Any]:
        """Compute dataset boundaries. Returns values and updates self.stats.

        Returns:
            dict: Dict includes "date_first_video", and "date_last_video"
        """

        stats = {
            "date_first_video": self.data["date"].min(),
            "date_last_video": self.data["date"].max(),
        }
        self.stats.update(stats)
        return stats

    def compute_video_counts(self) -> dict[str, Any]:
        """Compute video counts. Returns values and updates self.stats.

        Returns:
            dict: Dict includes "total_videos", "videos_per_day",
                "total_videos_unique", and "total_days_with_activity"
        """

        total_videos = len(self.data.index)
        total_videos_unique = self.data["link"].nunique()

        min_date, max_date = self._get_min_max_dates()

        n_days = (max_date - min_date).days
        n_days += 1  # correct interval length to count both upper and lower date

        videos_per_day = total_videos / n_days
        n_unique_dates = self.data["date"].dt.date.nunique()

        stats = {
            "total_videos": total_videos,
            "total_videos_unique": total_videos_unique,
            "videos_per_day": videos_per_day,
            "total_days_with_activity": n_unique_dates,
        }
        self.stats.update(stats)
        return stats

    def compute_peak_activity(self) -> dict[str, Any]:
        """Compute peak activity stats. Returns values and updates self.stats.

        Returns:
            dict: Dict includes "peak_day_date", "peak_day_video_count",
                and "peak_hour"
        """

        date, count = data_utils.get_most_occurring_date(self.data["date"])
        hour = data_utils.get_most_occurring_hour(self.data["hour"])

        stats = {
            "peak_day_date": date,
            "peak_day_video_count": count,
            "peak_hour": hour,
        }
        self.stats.update(stats)
        return stats

    def compute_session_statistics(
        self,
        cache_interim_result: bool = True,  # noqa: FBT002
    ) -> dict[str, Any]:
        """Compute session statistics. Returns values and updates self.stats.

        Args:
            cache_interim_result: If True, list of computed durations per video
                is stored at the class level.

        Returns:
            dict: Dict includes:

                - "avg_session_duration_seconds"
                - "avg_videos_per_session"
                - "avg_seconds_per_video"
        """

        session_stats: pd.DataFrame = data_utils.get_usage_sessions(
            self.data["date"],
            self.session_threshold_seconds,
        )

        durations_per_video = self._get_durations_per_video()

        # Cache durations per video
        if cache_interim_result:
            self.durations_per_video = durations_per_video

        stats = {
            "avg_session_duration_seconds": session_stats["duration_seconds"].mean(),
            "avg_videos_per_session": session_stats["num_entries"].mean(),
            "avg_seconds_per_video": durations_per_video.mean(),
        }
        self.stats.update(stats)

        return stats

    def compute_scrolling_statistics(
        self,
        threshold_options: list | None = None,
        target_percentage: int = 50,
        load_cached_durations: bool = True,  # noqa: FBT002
    ) -> dict[str, Any]:
        # Get durations per video
        if load_cached_durations:
            durations_per_video = self.durations_per_video
        else:
            durations_per_video = None

        if durations_per_video is None:
            durations_per_video = self._get_durations_per_video()

        # Find threshold that accounts for >= target_percentag of videos
        found_meaningful_threshold = False
        scroll_percentage = None
        scroll_seconds = None
        total_videos = durations_per_video.size

        if total_videos > 0:
            threshold_options = threshold_options or [3, 5, 10]
            for threshold in threshold_options:
                count = sum(1 for t in durations_per_video if t <= threshold)
                percentage = count / total_videos * 100

                if percentage >= target_percentage:
                    found_meaningful_threshold = True
                    scroll_percentage = round(percentage)
                    scroll_seconds = threshold
                    break

        # Fallback: use median
        if not found_meaningful_threshold and total_videos > 0:
            scroll_percentage = 50
            scroll_seconds = round(durations_per_video.median())

        stats = {
            "scroll_threshold_pct": scroll_percentage,
            "scroll_threshold_sec": scroll_seconds,
        }

        self.stats.update(stats)
        return stats

    def get_top_video(self) -> dict[str, Any]:
        """Get most watched video. Returns values and updates self.stats.

        If multiple videos share the highest view count, the one whose ID
        occurs first in alphabetical order is returned.

        Returns:
            dict: Dict includes "top_video_id", "top_video_seen_count",
                and "top_video_last_seen_date"
        """

        video_link, count = data_utils.get_most_occurring_string(self.data["link"])
        watch_dates = self.data.loc[self.data["link"] == video_link]["date"]
        video_id = video_link.rstrip("/").split("/")[-1]
        stats = {
            "top_video_id": video_id,
            "top_video_seen_count": count,
            "top_video_last_seen_date": watch_dates.max(),
        }
        self.stats.update(stats)
        return stats

    def get_date_hour_matrix(self) -> pd.DataFrame:
        """Get date hour matrix from given series.

        Creates a matrix showing the count of occurrences for each date-hour
        combination.

        Returns:
            pd.DataFrame: The date-hour matrix.
        """

        min_date, max_date = self._get_min_max_dates()
        return data_utils.get_date_hour_matrix(
            self.data["date"],
            min_date,
            max_date,
        )

    def _get_min_max_dates(self) -> tuple[datetime.datetime, datetime.datetime]:
        """Return min and max dates.

        For interval scope, min and max dates are the interval start and end dates.
        For full scope, min and max dates are the dates of first and last recorded
        videos.
        """

        if self.scope == StatisticsScope.INTERVAL:
            min_date = self.interval_start
            max_date = self.interval_end
        else:
            min_date = self.data["date"].min()
            max_date = self.data["date"].max()

        return min_date, max_date

    def _get_durations_per_video(self) -> pd.Series:
        durations_per_video = data_utils.get_times_between_timestamps(self.data["date"])
        # Drop timegaps that are larger than or equal to the session_threshold
        return durations_per_video[
            durations_per_video.to_numpy() < self.session_threshold_seconds
        ]
