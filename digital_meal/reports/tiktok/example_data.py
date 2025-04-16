import random
from datetime import timedelta

import numpy as np
from django.utils import timezone

from digital_meal.reports.utils_shared.example_data import (
    generate_hourly_shares, random_string, random_time_in_range)


def generate_synthetic_watch_history(start_date, days=500):
    """
    Generate a synthetic TikTok watch history dataset.

    :param start_date: The end date for the dataset (most recent day).
    :param days: Number of days to go back.
    :return: A dictionary mimicking the YouTube watch history JSON format.
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
            viewing_times += [random_time_in_range(hour, 0, hour, 59) for _ in range(num_videos_this_hour)]

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
