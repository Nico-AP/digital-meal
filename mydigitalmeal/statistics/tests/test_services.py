import datetime

import pandas as pd
from django.test import TestCase

from mydigitalmeal.statistics.models.base import StatisticsScope
from mydigitalmeal.statistics.services.tiktok_statistics import (
    WatchHistoryStatisticsGenerator,
)


class TestWatchHistoryStatisticsGenerator(TestCase):
    def setUp(self):
        """Set up test data for all tests."""
        self.sample_data = [
            {"Date": "2024-01-15 10:00:00", "Link": "video123"},
            {"Date": "2024-01-15 10:05:00", "Link": "video456"},
            {"Date": "2024-01-15 10:10:00", "Link": "video123"},
            {"Date": "2024-01-16 14:00:00", "Link": "video789"},
        ]

        self.generator_full = WatchHistoryStatisticsGenerator(
            watch_history=self.sample_data,
            scope=StatisticsScope.FULL,
        )

    def test_load_and_filter_data(self):
        """Test that data is loaded and has correct shape."""
        self.assertEqual(len(self.generator_full.data), 4)
        self.assertIn("date", self.generator_full.data.columns)
        self.assertIn("hour", self.generator_full.data.columns)
        self.assertIn("link", self.generator_full.data.columns)

    def test_load_and_filter_data_interval(self):
        """Test that interval filtering works correctly."""
        generator_interval = WatchHistoryStatisticsGenerator(
            watch_history=self.sample_data,
            scope=StatisticsScope.INTERVAL,
            interval_start=datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.UTC),
            interval_end=datetime.datetime(2024, 1, 15, 23, 59, tzinfo=datetime.UTC),
        )
        # Should only include the 3 videos from Jan 15
        self.assertEqual(len(generator_interval.data), 3)

    def test_get_scope_fields_full(self):
        """Test scope fields for FULL scope."""
        result = self.generator_full.get_scope_fields()

        self.assertEqual(result["scope"], StatisticsScope.FULL)
        self.assertNotIn("interval_start", result)
        self.assertNotIn("interval_end", result)

    def test_get_scope_fields_interval(self):
        """Test scope fields for INTERVAL scope."""
        start = datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.UTC)
        end = datetime.datetime(2024, 1, 16, 23, 59, tzinfo=datetime.UTC)

        generator = WatchHistoryStatisticsGenerator(
            watch_history=self.sample_data,
            scope=StatisticsScope.INTERVAL,
            interval_start=start,
            interval_end=end,
        )
        result = generator.get_scope_fields()

        self.assertEqual(result["scope"], StatisticsScope.INTERVAL)
        self.assertEqual(result["interval_start"], start)
        self.assertEqual(result["interval_end"], end)

    def test_get_dataset_bounds(self):
        """Test dataset boundary calculation."""
        result = self.generator_full.get_dataset_bounds()

        self.assertIn("date_first_video", result)
        self.assertIn("date_last_video", result)
        self.assertIsNotNone(result["date_first_video"])
        self.assertIsNotNone(result["date_last_video"])

    def test_compute_video_counts(self):
        """Test video count calculations."""
        result = self.generator_full.compute_video_counts()

        self.assertEqual(result["total_videos"], 4)
        self.assertEqual(result["total_videos_unique"], 3)
        self.assertEqual(result["videos_per_day"], (4 / 2))
        self.assertEqual(result["total_days_with_activity"], 2)

    def test_compute_video_counts_one_day(self):
        """Test video count calculations."""
        sample_data = [
            {"Date": "2024-01-15 10:00:00", "Link": "video123"},
            {"Date": "2024-01-15 10:01:00", "Link": "video123"},
        ]
        generator = WatchHistoryStatisticsGenerator(
            watch_history=sample_data,
            scope=StatisticsScope.FULL,
        )
        result = generator.compute_video_counts()

        self.assertEqual(result["total_videos"], 2)
        self.assertEqual(result["total_videos_unique"], 1)
        self.assertEqual(result["videos_per_day"], (2 / 1))
        self.assertEqual(result["total_days_with_activity"], 1)

    def test_compute_peak_activity(self):
        """Test peak activity calculation."""
        result = self.generator_full.compute_peak_activity()

        self.assertIn("peak_day_date", result)
        self.assertIn("peak_day_video_count", result)
        self.assertIn("peak_hour", result)
        # Jan 15 has 3 videos, Jan 16 has 1
        self.assertEqual(result["peak_day_video_count"], 3)

    def test_compute_session_statistics(self):
        """Test session statistics calculation."""
        result = self.generator_full.compute_session_statistics()

        self.assertIn("avg_session_duration_seconds", result)
        self.assertIn("avg_videos_per_session", result)
        self.assertIn("avg_seconds_per_video", result)

    def test_generate_all(self):
        """Test that generate_all returns complete statistics."""
        result = self.generator_full.generate_all()

        # Check all expected keys are present
        expected_keys = [
            "scope",
            "date_first_video",
            "date_last_video",
            "total_videos",
            "total_videos_unique",
            "videos_per_day",
            "total_days_with_activity",
            "peak_day_date",
            "peak_day_video_count",
            "peak_hour",
            "avg_session_duration_seconds",
            "avg_videos_per_session",
            "avg_seconds_per_video",
            "top_video_id",
            "top_video_seen_count",
        ]

        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_generate_all_single_video(self):
        """Test that generate_all returns complete statistics."""
        generator = WatchHistoryStatisticsGenerator(
            watch_history=[{"Date": "2024-01-15 10:00:00", "Link": "video123"}],
            scope=StatisticsScope.FULL,
        )
        result = generator.generate_all()

        self.assertEqual(result["total_videos"], 1)
        self.assertEqual(result["videos_per_day"], 1.0)

    # TODO: Double check this test.
    def test_generate_all_with_empty_data_raises_error(self):
        """Test generate_all handles empty data gracefully."""
        generator = WatchHistoryStatisticsGenerator(
            watch_history=[{"Date": "2024-01-15 10:00:00", "Link": "video123"}],
            scope=StatisticsScope.FULL,
        )
        generator.data = pd.DataFrame([])
        result = generator.generate_all()

        self.assertTrue(result)

    def test_top_video_calculation(self):
        """Test that most watched video is identified correctly."""
        result = self.generator_full.get_top_video()

        # video123 appears twice, others appear once
        self.assertEqual(result["top_video_id"], "video123")
        self.assertEqual(result["top_video_seen_count"], 2)

    def test_get_durations_per_video(self):
        sample_data = [
            {"Date": "2024-01-15 10:00:00", "Link": "video123"},
            {"Date": "2024-01-15 10:00:13", "Link": "video123"},
            {"Date": "2024-01-15 10:00:05", "Link": "video456"},
            {"Date": "2024-01-16 14:00:00", "Link": "video789"},
            {"Date": "2024-01-16 14:00:05", "Link": "video012"},
        ]

        generator = WatchHistoryStatisticsGenerator(
            watch_history=sample_data,
            scope=StatisticsScope.FULL,
        )

        result = generator._get_durations_per_video()
        expected = [5, 8, 5]
        self.assertEqual(result.to_list(), expected)

    def test_compute_scrolling_statistics(self):
        test_cases = [
            # durations, expected_pct, expected_sec, description
            ([], None, None, "No videos"),
            ([1, 2, 3, 4, 5, 6, 20, 30, 40, 50], 50, 5, "threshold at 5s"),
            ([1, 1, 2, 2, 3, 3, 3, 8, 9, 10], 70, 3, "early threshold at 3s"),
            ([6, 7, 8, 9, 10, 11, 12, 50, 60, 100], 50, 10, "threshold at 10s"),
            ([15, 20, 25, 30, 35, 40, 45, 50, 55, 60], 50, 38, "fallback to median"),
            ([1, 1, 1, 2, 2, 2, 3, 3, 3, 3], 100, 3, "all short videos"),
            (
                [1, 2, 3, 4, 5, 100, 100, 100, 100, 100],
                50,
                5,
                "exactly 50% at threshold",
            ),
        ]

        for durations, expected_pct, expected_sec, desc in test_cases:
            with self.subTest(desc=desc):
                self.generator_full.durations_per_video = pd.Series(durations)
                result = self.generator_full.compute_scrolling_statistics()
                expected = {
                    "scroll_threshold_pct": expected_pct,
                    "scroll_threshold_sec": expected_sec,
                }
                self.assertEqual(result, expected)
