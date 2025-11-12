import datetime
import random
from datetime import time

import numpy as np


def generate_hourly_shares(weekend: bool = False) -> dict:
    """Generate hourly shares.

    Generates a dictionary with 24-hour time slots and their respective random
    share values, based on different probability distributions for different
    times of the day.

    Args:
        weekend: If True, generate shares that are more evenly spread over a day.

    Returns:
        dict: A dictionary mapping each hour (0-23) to a random share within
            its assigned range.
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

def random_time_in_range(
        hour_start: int,
        min_start: int,
        hour_end: int,
        min_end: int
) -> datetime.time:
    """Generate a random time object between the given range."""
    return time(
        hour=random.randint(hour_start, hour_end),
        minute=random.randint(min_start, min_end),
        second=random.randint(0, 59)
    )

def random_string(length: int) -> str:
    """Generate a random alphanumeric string."""
    return ''.join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length))
