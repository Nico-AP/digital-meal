import random
from datetime import timedelta, time

import numpy as np
from django.utils import timezone


def generate_synthetic_watch_history(start_date, days=500):
    """
    Generate a synthetic YouTube watch history dataset.

    :param start_date: The end date for the dataset (most recent day).
    :param days: Number of days to go back.
    :return: A dictionary mimicking the YouTube watch history JSON format.
    """

    history_data = []
    current_date = start_date

    estimated_videos = days * 20  # Assume 40 videos max per day for estimation
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


def generate_synthetic_search_history(start_date, days=500):
    """
    Generate a synthetic YouTube search history dataset.

    :param start_date: The end date for the dataset (most recent day).
    :param days: Number of days to go back.
    :return: A dictionary mimicking the YouTube search history JSON format.
    """
    history_data = []
    current_date = start_date

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


def generate_hourly_shares(weekend=False):
    """
    Generate a dictionary with 24-hour time slots and their respective random share values,
    based on different probability distributions for different times of the day.

    :return: A dictionary mapping each hour (0-23) to a random share within its assigned range.
    """
    # Define custom share ranges for different periods of the day
    if not weekend:
        beta_ranges = {
            "night": (2, 8),  # 00:00 - 05:59 Low viewing activity
            "morning": (6, 4),  # 06:00 - 08:59 Morning commute
            "afternoon": (3, 6),  # 09:00 - 16:59 Lower activity due to work/school
            "evening_commute": (8, 3),  # 17:00 - 18:59 Evening commute
            "evening": (10, 2),  # 19:00 - 22:59 Peak viewing hours
            "late_night": (4, 5)  # 23:00 - 23:59
        }
    elif weekend:
        beta_ranges = {
            "night": (6, 8),  # 00:00 - 05:59 Low viewing activity
            "morning": (2, 4),  # 06:00 - 08:59
            "afternoon": (7, 2),  # 09:00 - 16:59
            "evening_commute": (7, 3),  # 17:00 - 18:59
            "evening": (10, 2),  # 19:00 - 22:59
            "late_night": (5, 5)  # 23:00 - 23:59
        }

    # Assign share ranges based on the hour of the day
    hourly_shares = {}
    for hour in range(24):
        if 0 <= hour < 6:
            hourly_shares[hour] = np.random.beta(*beta_ranges["night"])
        elif 6 <= hour < 9:
            hourly_shares[hour] = np.random.beta(*beta_ranges["morning"])
        elif 9 <= hour < 17:
            hourly_shares[hour] = np.random.beta(*beta_ranges["afternoon"])
        elif 17 <= hour < 19:
            hourly_shares[hour] = np.random.beta(*beta_ranges["evening_commute"])
        elif 19 <= hour < 23:
            hourly_shares[hour] = np.random.beta(*beta_ranges["evening"])
        else:
            hourly_shares[hour] = np.random.beta(*beta_ranges["late_night"])

    return hourly_shares


def generate_repeating_titles(num_titles=10000, repeat_fraction=0.01):
    """
    Generate a mix of unique and repeating video titles.

    :param num_titles: Total number of titles to generate.
    :param repeat_fraction: Fraction of titles that should be reused (e.g., 0.01 = 1% repeating).
    :return: A list of generated titles with some repetition.
    """
    unique_titles = [generate_random_title() for _ in range(int(num_titles * (1 - repeat_fraction)))]
    repeated_titles = random.choices(unique_titles, k=int(num_titles * repeat_fraction))  # Choose some titles to repeat
    all_titles = unique_titles + repeated_titles
    random.shuffle(all_titles)  # Mix them randomly
    return all_titles


def random_time_in_range(hour_start, min_start, hour_end, min_end):
    """Generate a random time object between the given range."""
    return time(
        hour=random.randint(hour_start, hour_end),
        minute=random.randint(min_start, min_end),
        second=random.randint(0, 59)
    )


def random_string(length):
    """Generate a random alphanumeric string (e.g., YouTube video ID)."""
    return ''.join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length))


def generate_random_title():
    """Generate a random video title using a mix of words and numbers."""
    words = ["Epic", "Crazy", "Ultimate", "Weird", "Amazing", "Unbelievable", "Funny", "Super", "Mega", "Best", "Worst",
             "Insane"]
    return f"{random.choice(words)} {random_string(5)} {random.randint(1, 1000)}"


def generate_random_channel_name():
    """Generate a random YouTube channel name."""
    prefixes = ["Tech", "Gaming", "Vlogs", "Music", "Epic", "NextGen", "Daily", "Mega", "Future", "Weird"]
    suffixes = ["World", "Stream", "Nation", "Explorer", "Insider", "Central", "Uncut", "Vision", "Channel"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"