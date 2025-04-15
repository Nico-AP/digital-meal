import pandas as pd

from datetime import datetime, timedelta
from dateutil.parser import parse
from statistics import mean, median


def get_entries_in_date_range(entries, date_min, date_max=datetime.now()):
    """
    Filter a series to only keep entries recorded in a given date range.
    """
    if (date_min.tzinfo is not None and
            date_min.tzinfo.utcoffset(date_min) is not None):
        timezone = date_min.tzinfo
        date_max = date_max.replace(tzinfo=timezone)
    else:
        date_max = date_max.replace(tzinfo=None)

    result = []
    for entry in entries:
        if 'time' not in entry:
            continue

        if date_min <= parse(entry['time']) <= date_max:
            result.append(entry)
    return result

def normalize_datetime(date, mode='d'):
    """
    Normalizes a datetime object to a specific day, week, month, or year.
    :param date: A datetime object.
    :param mode: The normalization mode:
        'd' - Daily: returns date.
        'w' - Weekly: returns date of first day of the week to which date
            belongs.
        'm' - Monthly: returns the 15th of the month of date.
        'y' - Yearly: returns the 1st of July of the year of date.
        Note: Time is in each case set to 00:00.
    :return: A datetime object.
    """
    date = date.date()

    if mode == 'd':
        return datetime.combine(date,
                                datetime.min.time())

    elif mode == 'w':
        week_start = date - timedelta(days=date.weekday())
        return datetime.combine(week_start,
                                datetime.min.time())

    elif mode == 'm':
        return datetime.combine(date.replace(day=15),
                                datetime.min.time())

    elif mode == 'y':
        return datetime.combine(date.replace(day=1, month=7),
                                datetime.min.time())

    else:
        print('Invalid mode.')
        return None

def summarize_list(li, n=1, mode='sum'):
    """
    Summarizes a list of numbers as sum, median, or mean.
    :param li: A list of numbers
    :param n: The number of reference cases.
    :param mode: Defines the summary logic:
        'sum' - Returns the sum over all list elements.
        'median' - Returns the median of the list elements.
        'mean' - Returns the mean of the list elements.
    :return: Number
    """
    while len(li) < n:
        li.append(0)

    if mode == 'sum':
        return sum(li)
    elif mode == 'median':
        return median(li)
    elif mode == 'mean':
        return mean(li)
    else:
        print('Invalid mode.')
        return None

def get_summary_counts_per_date(data, ref='d', base='sum'):
    """
    Summarizes date occurrences across dates and persons.

    :param data: A list of lists where the inner lists hold the data related to
        one person ([[{P1, e1}, {p1, e2}], [{P2, e1}, {P2, e2}]]).
    :param ref: Defines the reference of the date counts:
        'd' - counts per day (default)
        'w' - counts per week (attributed to the date of the first day of
            the week)
        'm' - counts per month (attributed to the 15th of the month)
        'y' - counts per year (attributed to the 1st of July of the year)
    :param base: Defines how the counts will be summarized:
        'sum' - Sum over all persons
        'mean' - Mean over all persons
        'median' - Median over all persons
    :return: Dictionary containing summary counts per date ({'date': count})
    """
    n_cases = len(data)
    dates_combined = []
    for p in data:
        dates_combined += p

    date_list = [normalize_datetime(d, mode=ref) for d in dates_combined]

    # Prepare count dictionary.
    counts = {d: [] for d in set(date_list)}

    # Add counts per person.
    for p in data:
        normalized_dates = [normalize_datetime(d, mode=ref) for d in p]
        individual_date_list = pd.Series(normalized_dates).value_counts()
        for index, value in individual_date_list.items():
            counts[index].append(value)

    # iterate over counts and sum/median/average (whatever)
    for key, value in counts.items():
        counts[key] = summarize_list(value, n=n_cases, mode=base)

    return counts
