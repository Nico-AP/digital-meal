import random
from datetime import timedelta, date

import numpy as np
from django.utils import timezone

from digital_meal.reports.utils.shared.example_data import (
    generate_hourly_shares,
    random_string,
    random_time_in_range
)


def generate_synthetic_watch_history(
        start_date: date,
        days: int = 500
) -> dict:
    """Generate a synthetic TikTok watch history dataset.

    Args:
        start_date: The end date for the dataset (most recent day).
        days: Number of days to go back.

    Returns:
        dict: A dictionary mimicking the YouTube watch history JSON format.
    """

    history_data = []
    current_date = start_date

    for _ in range(days):
        if current_date.weekday() < 5:  # Weekdays (Mon-Fri)
            num_entries = max(5, np.random.poisson(lam=100))
            hourly_shares = generate_hourly_shares()

        else:
            num_entries = max(5, np.random.poisson(lam=250))
            hourly_shares = generate_hourly_shares(weekend=True)

        # Normalize hourly shares so they sum up to 1 for weighted sampling
        total_share = sum(hourly_shares.values())
        normalized_shares = {hour: share / total_share for hour, share in hourly_shares.items()}

        # Assign videos across the 24 hours based on share weights
        viewing_times = []
        for hour, share_weight in normalized_shares.items():
            num_videos_this_hour = max(0, int(num_entries * share_weight * random.uniform(0.9, 1.1)))  # Add slight randomness
            viewing_times.extend([random_time_in_range(hour, 0, hour, 59) for _ in range(num_videos_this_hour)])

        # Generate entries for the day
        for watch_time in sorted(viewing_times):
            watch_datetime = timezone.datetime.combine(current_date, watch_time)

            entry = {
                "Date": watch_datetime.isoformat(),
                "Link": f"https://www.tiktok.com/@/video/{random_string(19)}/",
            }

            history_data.append(entry)

        # Move to the previous day
        current_date -= timedelta(days=1)

    # Add favorite video
    for _ in range(5):
        entry = {
            "Date": current_date.isoformat(),
            "Link": f"https://www.tiktok.com/@/video/7486877232867101974/"
        }
        history_data.append(entry)

    return {
        "time_submitted": timezone.now().isoformat() + "Z",
        "consent": True,
        "status": "success",
        "data": history_data
    }


def generate_synthetic_search_history(
        latest_date: date,
        days: int = 500
) -> dict:
    """Generate a synthetic TikTok search history dataset.

    Args:
        latest_date: The end date for the dataset (most recent day).
        days: Number of days to go back.

    Returns:
        A dictionary mimicking the TikTok search history JSON format. Contains
        the following fields: "SearchTerm", "Date".
    """
    history_data = []
    current_date = latest_date

    for _ in range(days):
        n_searches = random.randint(0, 5)
        search_times = [random_time_in_range(0, 0, 23, 59) for _ in range(n_searches)]

        # Generate entries for the day
        for search_time in sorted(search_times):
            search_datetime = timezone.datetime.combine(current_date, search_time)
            entry = {
                "SearchTerm": generate_random_search_term(),
                "Date": search_datetime.isoformat(),
            }

            history_data.append(entry)

        # Move to the previous day
        current_date -= timedelta(days=1)

    return {
        "time_submitted": timezone.now().isoformat() + "Z",
        "consent": True,
        "status": "success",
        "data": history_data
    }


def generate_random_search_term() -> str:
    """Generate a random search term.

    Returns:
        str: A random search term.
    """
    prefixes = ["Tech", "Gaming", "Vlogs", "Music", "Epic", "NextGen", "Daily", "Mega", "Future", "Weird"]
    suffixes = ["World", "Stream", "Nation", "Explorer", "Insider", "Central", "Uncut", "Vision", "Channel"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"
