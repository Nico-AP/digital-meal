import random
from datetime import timedelta, date

import numpy as np
from django.utils import timezone

from digital_meal.reports.utils.shared.example_data import (
    random_string, random_time_in_range, generate_hourly_shares)


def generate_synthetic_watch_history(
        latest_date: date,
        days: int = 500
) -> dict:
    """
    Generate a synthetic YouTube watch history dataset.

    Args:
        latest_date: The end date for the dataset (most recent day).
        days: Number of days to go back.

    Returns:
        A dictionary mimicking the YouTube watch history JSON format. Contains
        the following fields: "time_submitted", "consent", "status", "data".
    """

    history_data = []
    current_date = latest_date

    estimated_videos = days * 20  # Assume 20 videos max per day for estimation
    title_pool = generate_repeating_titles(num_titles=estimated_videos, repeat_fraction=0.01)

    title_index = 0  # Track the title pool usage

    for _ in range(days):
        if current_date.weekday() < 5:  # Weekdays (Mon-Fri)
            num_entries = max(5, np.random.poisson(lam=25))
            hourly_shares = generate_hourly_shares()

        else:
            num_entries = max(5, np.random.poisson(lam=40))
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
                "title": title_pool[title_index % len(title_pool)],
                "titleUrl": f"https://www.youtube.com/watch?v={random_string(11)}",
                "time": watch_datetime.isoformat(),
                "subtitles": [{"name": generate_random_channel_name(),
                               "url": f"https://www.youtube.com/channel/{random_string(20)}"}]
            }

            history_data.append(entry)

        # Move to the previous day
        current_date -= timedelta(days=1)

    # Add favorite video
    for _ in range(5):
        entry = {
            "title": "Discover the University of Zurich in 100 seconds",
            "titleUrl": f"https://www.youtube.com/watch?v=_kFexLYRGrA",
            "time": current_date.isoformat(),
            "subtitles": [{"name": "UZH",
                           "url": f"https://www.youtube.com/channel/@uzhch"}]
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
    """Generate a synthetic YouTube search history dataset.

    Args:
        latest_date (datetime.datetime): The end date for the dataset (most recent day).
        days (int): Number of days to go back.

    Returns:
        A dictionary mimicking the YouTube search history JSON format. Contains
        the following fields: "time_submitted", "consent", "status", "data".
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
                "title": generate_random_channel_name(),
                "titleUrl": f"https://www.youtube.com/watch?v={random_string(11)}",
                "time": search_datetime.isoformat(),
                "activityControls": ["YouTube-Suchverlauf"]
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


def generate_repeating_titles(
        num_titles: int = 10000,
        repeat_fraction: float = 0.01
) -> list:
    """
    Generate a mix of unique and repeating video titles.

    Args:
        num_titles (int): Number of titles to generate.
        repeat_fraction (float): Fraction of titles that should be reused
            (e.g., 0.01 = 1% repeating).

    Returns:
        list: A list of generated titles with some repetition.
    """
    unique_titles = [generate_random_title() for _ in range(int(num_titles * (1 - repeat_fraction)))]
    repeated_titles = random.choices(unique_titles, k=int(num_titles * repeat_fraction))  # Choose some titles to repeat
    all_titles = unique_titles + repeated_titles
    random.shuffle(all_titles)  # Mix them randomly
    return all_titles


def generate_random_title() -> str:
    """
    Generate a random video title using a mix of words and numbers.

    Returns:
        str: A random video title.
    """
    words = ["Epic", "Crazy", "Ultimate", "Weird", "Amazing", "Unbelievable", "Funny", "Super", "Mega", "Best", "Worst",
             "Insane"]
    return f"{random.choice(words)} {random_string(5)} {random.randint(1, 1000)}"


def generate_random_channel_name() -> str:
    """
    Generate a random YouTube channel name.

    Returns:
        str: A random YouTube channel name.
    """
    prefixes = ["Tech", "Gaming", "Vlogs", "Music", "Epic", "NextGen", "Daily", "Mega", "Future", "Weird"]
    suffixes = ["World", "Stream", "Nation", "Explorer", "Insider", "Central", "Uncut", "Vision", "Channel"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"
