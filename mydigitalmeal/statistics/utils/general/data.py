from datetime import date, datetime

import pandas as pd


def get_most_occurring_hour(s: pd.Series) -> int:
    """Return the hour occurring most often in given series.

    Assumes that series consists of integer value in the range(0, 24).
    If two hour values occur equally often, returns the larger value.

    Args:
        s: Pandas series containing hour values.

    Returns:
        int: Value of hour that occurred most often.
    """
    hour_counts = s.value_counts().sort_index(ascending=False)
    hour = hour_counts.idxmax()
    max_hour = 24
    if int(hour) == max_hour:
        return 0
    return int(hour)


def get_most_occurring_date(
    dates: pd.Series,
) -> tuple[datetime, int] | tuple[None, None]:
    """Return the date and count of most often occurring date in given series.

    If two dates occur equally often, returns the more recent date.

    Args:
        dates: Pandas series containing date values.

    Returns:
        tuple[datetime, int]: Date and count of most often occurring date.
    """
    if len(dates) == 0:
        return None, None

    date_counts = dates.dt.date.value_counts().sort_index(ascending=False)
    date = date_counts.idxmax()
    date_count = int(date_counts.max())
    return date, date_count


def get_most_occurring_string(
    strings: pd.Series,
) -> tuple[str, int] | tuple[None, None]:
    """Return the value and count of most often occurring string in given series.

    If two strings occur equally often, returns the one occurring first
    alphabetically.

    Args:
        strings: Pandas series containing string values.

    Returns:
        tuple[str, int]: Value and count of most often occurring string.
    """
    if len(strings) == 0:
        return None, None

    counts = strings.value_counts().sort_index(ascending=True)
    value = counts.idxmax()
    value_count = int(counts.max())
    return value, value_count


def get_date_hour_matrix(
    dates: pd.Series,
    min_date: date,
    max_date: date,
) -> pd.DataFrame:
    """Get date hour matrix from given series.

    Creates a matrix showing the count of occurrences for each date-hour
    combination. The resulting DataFrame has dates as rows (y-axis)
    and hours (0-23) as columns (x-axis). Missing dates within the specified
    range and hours with no occurrences are filled with 0.

    Args:
        dates: Pandas series containing datetime values.
        min_date: Minimum datetime value to include in the matrix.
        max_date: Maximum datetime value to include in the matrix.

    Returns:
        pd.DataFrame: The date-hour matrix with occurrence count as values.
            Index: dates from min_date to max_date (inclusive)
            Columns: hours from 0 to 23
            Values: count of occurrences for each date-hour combination
    """
    date_hour_df = pd.DataFrame(
        {
            "date": dates.dt.date,
            "hour": dates.dt.hour,
        },
    )

    matrix = pd.crosstab(date_hour_df["date"], date_hour_df["hour"])

    # Get the full date range (including missing dates)
    date_range = pd.date_range(
        start=min_date,
        end=max_date,
        freq="D",
    ).date

    # Reindex to include all dates and all hours (0-23)
    return matrix.reindex(index=date_range, columns=range(24), fill_value=0)


def get_usage_sessions(
    timestamps: pd.Series,
    session_threshold: int,
) -> pd.DataFrame:
    """Identify usage sessions from a series of datetime values.

    A new session starts when the time gap between consecutive activities
    exceeds the specified threshold. For each identified session, calculates
    the number of entries and the total duration.

    Args:
        timestamps: Pandas series containing datetime values.
        session_threshold: Threshold of seconds without activities for a session
            to be considered over.

    Returns:
        pd.DataFrame: DataFrame with columns:
            - "session_id": Integer identifier for each session (starting at 0)
            - "start_time": Start datetime of the session
            - "end_time": End datetime of the session
            - "num_entries": Number of activities in the session
            - "duration_minutes": Duration of the session in minutes
    """
    timestamps_sorted = timestamps.sort_values().reset_index(drop=True)

    # Calculate time differences between consecutive entries
    time_diffs = timestamps_sorted.diff()

    # Identify session breaks (gaps > threshold)
    session_breaks = time_diffs > pd.Timedelta(seconds=session_threshold)

    # Assign session IDs with cumulative sum of True values
    session_ids = session_breaks.cumsum()

    # Group by session and calculate statistics
    sessions = pd.DataFrame(
        {
            "datetime": timestamps_sorted,
            "session_id": session_ids,
        },
    )

    session_stats = (
        sessions.groupby("session_id")
        .agg(
            start_time=("datetime", "min"),
            end_time=("datetime", "max"),
            num_entries=("datetime", "size"),
        )
        .reset_index()
    )

    # Calculate duration in minutes
    session_stats["duration_seconds"] = (
        session_stats["end_time"] - session_stats["start_time"]
    ).dt.total_seconds()

    return session_stats


def get_times_between_timestamps(timestamps: pd.Series) -> pd.Series:
    """Get a list of times (in seconds) between timestamps in a series.

    Args:
        timestamps: Series of timestamps.

    Returns:
        pd.Series: Series of times (in seconds) between timestamps.
    """
    timestamps_sorted = timestamps.sort_values().reset_index(drop=True)
    time_diffs = timestamps_sorted.diff()

    if len(time_diffs) == 0:
        return pd.Series([])

    return time_diffs.dt.total_seconds().dropna()
