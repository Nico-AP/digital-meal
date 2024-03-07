# util functions to manipulate youtube data

import pandas as pd
import random
import re

from datetime import datetime, timedelta
from dateutil.parser import parse
from statistics import mean, median


def get_video_ids(watch_history):
    """ Get a list containing only the video ids from the watch history. """
    video_ids = [
        d['titleUrl'].replace('https://www.youtube.com/watch?v=', '')
        for d in watch_history if 'titleUrl' in d
    ]
    return video_ids


def get_date_list(watch_history):
    """ Get a list containing the dates of all watched videos. """
    dates = [parse(d['time']) for d in watch_history if 'time' in d]
    return dates


def get_entries_in_date_range(entries, date_min, date_max=datetime.now()):
    """ Filter a series to only keep entries recorded in a given date range. """
    if date_min.tzinfo is not None and date_min.tzinfo.utcoffset(date_min) is not None:
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


def get_watched_video_urls(watch_history):
    """ Get a list containing the titleUrls of all watched videos. """
    video_urls = [d['titleUrl'].replace('https://www.youtube.com/watch?v=', '')
                  for d in watch_history if 'titleUrl' in d]
    return video_urls


def exclude_google_ads_videos(watch_history):
    """
    Excludes all videos shown through Google Ads from the watch history.
    """
    watched_videos = []
    for video in watch_history:
        if 'details' in video and len(video['details']) > 0:
            if video['details'][0]['name'] == 'From Google Ads':
                continue
            else:
                watched_videos.append(video)
        else:
            watched_videos.append(video)
    return watched_videos


def exclude_ads_from_search_history(search_history):
    """ Excludes all ads from search history. """
    history = []
    for entry in search_history:
        if 'activityControls' not in entry:
            continue

        if 'Web & App Activity' in entry['activityControls']:
            continue

        history.append(entry)

    return history


def clean_search_titles(search_history):
    """
    Delete pre- and postfixes from search titles.
    Supports takeouts in German, English, Italian, and French.
    """
    prefix_en = '^Searched for '
    prefix_de = '^Gesucht nach: '
    prefix_it = '^Hai cercato '
    prefix_fr = '^Vous avez recherché '
    r = '|'.join([prefix_en, prefix_de, prefix_it, prefix_fr])

    clean_searches = []
    for entry in search_history:
        if 'title' in entry:
            entry['title'] = re.sub(r, '', entry['title'])
        clean_searches.append(entry)

    return clean_searches


def get_video_title_dict(watch_history):
    """
    Create a dict with Video IDs as keys and video title as value.
    returns {'video_id': 'video_title', ...}
    """
    titles = {}
    for video in watch_history:
        if 'titleUrl' in video:
            video_id = video['titleUrl'].replace('https://www.youtube.com/watch?v=', '')
            title = video['title'].strip()
            titles[video_id] = title
    return titles


def get_most_watched_video(watch_history):
    """ Get ID and watch count of the most watched video in watch history. """
    video_urls = pd.Series(get_watched_video_urls(watch_history))
    # TODO: Make sure, the chosen favorite video is still available, i.e. has not been deleted.
    max_count = video_urls.value_counts().max()
    most_watched_urls = video_urls.value_counts()[video_urls.value_counts() == max_count]
    favorite_video = random.choice(most_watched_urls.keys().to_list())
    return {'id': favorite_video, 'n_watched': max_count}


def get_channels_from_history(watch_history):
    """ Get a list of the channel names of watched videos. """
    channels = []
    for video in watch_history:
        if 'subtitles' in video:
            subtitles = video['subtitles']
        else:
            continue

        if len(subtitles) > 0:
            if 'name' in subtitles[0]:
                channels.append(subtitles[0]['name'])

    return channels


def get_search_term_frequency(search_history, n_terms=None):
    """ Get a dict with search term and counts. """
    search_terms = pd.Series([t['title'] for t in search_history])
    x_labels = search_terms.value_counts().keys().to_list()
    y_values = search_terms.value_counts().values.tolist()

    if n_terms:
        if len(x_labels) > n_terms:
            x_labels = x_labels[:n_terms]
            y_values = y_values[:n_terms]

    searches = []
    for term in range(0, len(x_labels)):
        searches.append({'term': x_labels[term], 'count': y_values[term]})

    return searches


def normalize_datetime(date, mode='d'):
    """
    Normalizes a datetime object to a specific day, week, month, or year.
    :param date: A datetime object.
    :param mode: The normalization mode:
        'd' - Daily: returns date.
        'w' - Weekly: returns date of first day of the week to which date belongs.
        'm' - Monthly: returns the 15th of the month of date.
        'y' - Yearly: returns the 1st of July of the year of date.
        Note: Time is in each case set to 00:00.
    :return: A datetime object.
    """
    date = date.date()

    if mode == 'd':
        return datetime.combine(date, datetime.min.time())

    elif mode == 'w':
        week_start = date - timedelta(days=date.weekday())
        return datetime.combine(week_start, datetime.min.time())

    elif mode == 'm':
        return datetime.combine(date.replace(day=15), datetime.min.time())

    elif mode == 'y':
        return datetime.combine(date.replace(day=1, month=7), datetime.min.time())

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
        one person ([[{P1 e1}, {p2, e2}], [{P2, e1}, {P2, e2}]]).
    :param ref: Defines the reference of the date counts:
        'd' - counts per day (default)
        'w' - counts per week (attributed to the date of the first day of the week)
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
        individual_date_list = pd.Series([normalize_datetime(d, mode=ref) for d in p]).value_counts()
        for index, value in individual_date_list.items():
            counts[index].append(value)

    # iterate over counts and sum/median/average (whatever)
    for key, value in counts.items():
        counts[key] = summarize_list(value, n=n_cases, mode=base)

    return counts
