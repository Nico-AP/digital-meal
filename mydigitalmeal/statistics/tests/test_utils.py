import datetime

import pandas as pd
from django.test import TestCase

import mydigitalmeal.statistics.utils.general.data as data_utils
import mydigitalmeal.statistics.utils.tiktok.data as tiktok_utils


class TikTokDataLoaderTests(TestCase):
    def test_load_tiktok_watch_history_basic(self):
        """Test basic data loading."""
        data = [
            {"Date": "2024-01-15 10:00:00", "Link": "video123"},
            {"Date": "2024-01-15 14:30:00", "Link": "video456"},
        ]
        df_history = tiktok_utils.load_tiktok_watch_history(data)

        self.assertEqual(len(df_history), 2)
        self.assertIn("date", df_history.columns)
        self.assertIn("link", df_history.columns)
        self.assertIn("hour", df_history.columns)

    def test_load_tiktok_watch_history_hour_extraction(self):
        """Test that hour is extracted correctly."""
        data = [
            {"Date": "2024-01-15 10:00:00", "Link": "video123"},
            {"Date": "2024-01-15 14:30:00", "Link": "video456"},
        ]
        df_history = tiktok_utils.load_tiktok_watch_history(data)

        self.assertEqual(df_history.iloc[0]["hour"], 10)
        self.assertEqual(df_history.iloc[1]["hour"], 14)


class DataUtilsTests(TestCase):
    def test_get_most_occurring_hour(self):
        data = [
            {"hour": 12},
            {"hour": 12},
            {"hour": 14},
            {"hour": 24},
        ]
        df_hours = pd.DataFrame(data)
        hour = data_utils.get_most_occurring_hour(df_hours["hour"])
        self.assertEqual(hour, 12)

    def test_get_most_occurring_hour_24(self):
        data = [
            {"hour": 12},
            {"hour": 12},
            {"hour": 24},
            {"hour": 24},
            {"hour": 24},
        ]
        df_hours = pd.DataFrame(data)
        hour = data_utils.get_most_occurring_hour(df_hours["hour"])
        self.assertEqual(hour, 0)

    def test_get_most_occurring_hour_two_counts_equal(self):
        data = [
            {"hour": 12},
            {"hour": 14},
        ]
        df_hours = pd.DataFrame(data)
        hour = data_utils.get_most_occurring_hour(df_hours["hour"])
        self.assertEqual(hour, 14)

    def test_get_most_occurring_date(self):
        data = [
            {"date": "2025-10-10 12:00:00"},
            {"date": "2025-10-10 10:00:00"},
            {"date": "2025-10-09 10:00:00"},
            {"date": "2025-10-08 12:00:00"},
        ]
        df_dates = pd.DataFrame(data)
        df_dates["date"] = pd.to_datetime(df_dates["date"])
        date, count = data_utils.get_most_occurring_date(df_dates["date"])

        self.assertEqual(count, 2)
        self.assertEqual(date, datetime.date(2025, 10, 10))

    def test_get_most_occurring_date_empty(self):
        data = pd.Series([])
        date, count = data_utils.get_most_occurring_date(data)

        self.assertEqual(count, None)
        self.assertEqual(date, None)

    def test_get_most_occurring_date_two_counts_equal(self):
        data = [
            {"date": "2025-10-09 12:00:00"},
            {"date": "2025-10-10 10:00:00"},
            {"date": "2025-10-10 12:00:00"},
            {"date": "2025-10-09 10:00:00"},
        ]
        df_dates = pd.DataFrame(data)
        df_dates["date"] = pd.to_datetime(df_dates["date"])
        date, count = data_utils.get_most_occurring_date(df_dates["date"])

        self.assertEqual(count, 2)
        self.assertEqual(date, datetime.date(2025, 10, 10))

    def test_get_most_occurring_string(self):
        data = pd.Series(
            [
                "abc",
                "abc",
                "def",
            ],
        )
        value, count = data_utils.get_most_occurring_string(data)

        self.assertEqual(count, 2)
        self.assertEqual(value, "abc")

    def test_get_most_occurring_string_empty(self):
        data = pd.Series([])
        value, count = data_utils.get_most_occurring_string(data)

        self.assertEqual(count, None)
        self.assertEqual(value, None)

    def test_get_most_occurring_string_two_counts_equal(self):
        data = pd.Series(
            [
                "abc",
                "abc",
                "def",
                "def",
            ],
        )
        value, count = data_utils.get_most_occurring_string(data)

        self.assertEqual(count, 2)
        self.assertEqual(value, "abc")

    def test_get_hour_matrix(self):
        data = pd.Series(
            [
                datetime.datetime(2025, 10, 10, 2, 0, tzinfo=datetime.UTC),
                datetime.datetime(2025, 10, 10, 3, 0, tzinfo=datetime.UTC),
                datetime.datetime(2025, 10, 12, 4, 0, tzinfo=datetime.UTC),
            ],
        )
        min_date = datetime.date(2025, 10, 8)
        max_date = datetime.date(2025, 10, 11)

        result = data_utils.get_date_hour_matrix(data, min_date, max_date)
        self.assertEqual(result.shape, (4, 24))
        loc_date = datetime.date(2025, 10, 10)
        self.assertEqual(result.loc[loc_date, 2], 1)

        loc_date = datetime.date(2025, 10, 8)
        self.assertEqual(result.loc[loc_date, 2], 0)

    def test_get_usage_sessions(self):
        """Test session identification with multiple sessions."""
        dates = pd.Series(
            [
                pd.Timestamp("2024-01-15 10:00"),
                pd.Timestamp("2024-01-15 10:05"),
                pd.Timestamp("2024-01-15 10:10"),
                pd.Timestamp("2024-01-15 11:30"),  # 80 min gap - new session
                pd.Timestamp("2024-01-15 11:35"),
                pd.Timestamp("2024-01-15 14:00"),  # 145 min gap - new session
            ],
        )
        session_threshold = 60 * 60
        result = data_utils.get_usage_sessions(dates, session_threshold)

        # Check
        self.assertEqual(len(result), 3)

        # session 0
        self.assertEqual(result.loc[0, "session_id"], 0)
        self.assertEqual(result.loc[0, "num_entries"], 3)
        self.assertEqual(result.loc[0, "duration_seconds"], 600.0)
        self.assertEqual(result.loc[0, "start_time"], pd.Timestamp("2024-01-15 10:00"))
        self.assertEqual(result.loc[0, "end_time"], pd.Timestamp("2024-01-15 10:10"))

        # session 2
        self.assertEqual(result.loc[2, "session_id"], 2)
        self.assertEqual(result.loc[2, "num_entries"], 1)
        self.assertEqual(result.loc[2, "duration_seconds"], 0.0)

    def test_get_usage_sessions_empty(self):
        """Test with empty series."""
        dates = pd.Series([], dtype="datetime64[ns]")
        session_threshold = 60
        result = data_utils.get_usage_sessions(dates, session_threshold)
        self.assertEqual(len(result), 0)

    def test_get_times_between_timestamps(self):
        data = pd.Series(
            [
                datetime.datetime(2025, 10, 10, 10, 0, 0, tzinfo=datetime.UTC),
                datetime.datetime(2025, 10, 10, 10, 0, 5, tzinfo=datetime.UTC),
                datetime.datetime(2025, 10, 10, 10, 1, 0, tzinfo=datetime.UTC),
            ],
        )
        result = data_utils.get_times_between_timestamps(data)

        self.assertEqual(len(result), 2)
        self.assertListEqual(list(pd.Series([5.0, 55.0])), list(result))

    def test_get_times_between_timestamps_empty(self):
        data = pd.Series([])
        result = data_utils.get_times_between_timestamps(data)

        self.assertEqual(len(result), 0)
        self.assertListEqual(list(pd.Series([])), list(result))
