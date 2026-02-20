from typing import Any

import pandas as pd


def load_tiktok_watch_history(
    data: list[dict[str, Any]],
    date_key: str = "date",
) -> pd.DataFrame:
    """Load TikTok watch history data into pandas DataFrame.

    Args:
        data: List of dictionaries representing TikTok watch history data.
        date_key: Name of date column.

    Returns:
        pd.DataFrame: Pandas DataFrame containing TikTok watch history data.
    """

    df_tiktok_wh = pd.DataFrame(data)

    # convert column names to lower key
    df_tiktok_wh.columns = df_tiktok_wh.columns.str.lower()

    # Convert to datetime
    df_tiktok_wh[date_key] = pd.to_datetime(df_tiktok_wh[date_key], utc=True)

    # Add time column
    df_tiktok_wh["hour"] = df_tiktok_wh[date_key].dt.hour

    # TODO: Other cleaning steps?
    return df_tiktok_wh
