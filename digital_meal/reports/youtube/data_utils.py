import datetime

import pandas as pd
import random
import re

from dateutil.parser import parse


def get_video_ids(watch_history: list[dict]) -> list[str]:
    """
    Get a list containing only the video ids from the watch history.

    Args:
        watch_history (list[dict]): List of watch history data.

    Returns:
        list[str]: A list of video ids extracted from the 'titleUrl' key
        of watch history entries.
    """
    video_ids = [
        d['titleUrl'].replace('https://www.youtube.com/watch?v=', '')
        for d in watch_history if 'titleUrl' in d
    ]
    return video_ids


def get_date_list(watch_history: list[dict]) -> list[datetime.datetime]:
    """
    Get a list containing the dates of all watched videos.

    Args:
        watch_history (list[dict]): List of watch history data.

    Returns:
        list[dict]: A list of dates as datetime objects extracted from the 'time' key.
    """
    dates = [parse(d['time']) for d in watch_history if 'time' in d]
    return dates


def exclude_google_ads_videos(watch_history: list[dict]) -> list[dict]:
    """
    Excludes all videos shown through Google Ads from the watch history.

    Args:
        watch_history (list[dict]): List of watch history data.

    Returns:
        list[dict]: The watch history excluding videos shown through Google Ads.
    """
    ad_identifiers = [
        'from google ads',
        'von google anzeigen',
        'da programmi pubblicitari google',
        'des annonces google',
    ]
    watched_videos = []
    for video in watch_history:
        if 'details' not in video:
            watched_videos.append(video)
            continue

        if len(video['details']) == 0:
            watched_videos.append(video)
            continue

        if 'name' not in video['details'][0]:
            watched_videos.append(video)
            continue

        if video['details'][0]['name'].lower() in ad_identifiers:
            # Do not add video to watched videos.
            continue
        else:
            watched_videos.append(video)
            continue

    return watched_videos


def exclude_ads_from_search_history(search_history: list[dict]) -> list[dict]:
    """
    Excludes all ads from search history.

    Args:
        search_history (list[dict]): List of search history data.

    Returns:
        list[dict]: The search history excluding videos shown through Google Ads.
    """
    ad_identifiers = [
        'web & app activity',
        'web- & app-aktivitäten',
        'attività web e app',
        'activité sur le web et les applications'
    ]
    history = []
    for entry in search_history:
        if 'activityControls' not in entry:
            continue

        if any(item.lower() in ad_identifiers for item in entry['activityControls']):
            continue

        history.append(entry)

    return history


def clean_search_titles(search_history: list[dict]) -> list[dict]:
    """
    Delete pre- and postfixes from search titles.
    Supports takeouts in German, English, Italian, and French.

    Args:
        search_history (list): List of search history data.

    Returns:
        list: The search history with cleaned titles.
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


def clean_video_title(video_title: str) -> str:
    """
    Delete pre- and postfixes from video titles as exported from Google
    Takeout.
    Supports takeouts in German, English, Italian, and French.

    Args:
        video_title (str): Video title.

    Returns:
        str: The cleaned video title.
    """
    prefix_en = '^Watched '
    postfix_de = ' angesehen$'
    prefix_it = '^Hai guardato '
    prefix_fr = '^Vous avez regardé '
    r = '|'.join([prefix_en, prefix_it, prefix_fr, postfix_de])
    clean_title = re.sub(r, '', video_title)
    return clean_title


def get_video_title_dict(watch_history: list[dict]) -> dict:
    """
    Create a dict with Video IDs as keys and video title as value
    (e.g., {'video_id': 'video_title', ...}).

    Args:
        watch_history (list[dict]): List of watch history data.

    Returns:
        dict: Dict with Video IDs as keys and video title as value
    """
    titles = {}
    generic_url = 'https://www.youtube.com/watch?v='
    for video in watch_history:
        if 'titleUrl' in video:
            video_id = video['titleUrl'].replace(generic_url, '')
            title = video['title'].strip()
            titles[video_id] = title
    return titles


def get_most_watched_video(watch_history: list[dict]) -> dict:
    """
    Get ID and watch count of the most watched video in watch history (as dict).

    Args:
        watch_history (list[dict]): List of watch history data.

    Returns:
        dict: A dict of form:
            {'id': <id of fav video>, 'n_watched': <times video occurred>}
    """
    video_ids = pd.Series(get_video_ids(watch_history))
    # TODO: Make sure, the chosen favorite video is still available,
    # i.e. has not been deleted.
    max_count = video_ids.value_counts().max()
    video_counts = video_ids.value_counts()
    most_watched_ids = video_counts[video_counts == max_count]
    favorite_video = random.choice(most_watched_ids.keys().to_list())
    return {'id': favorite_video, 'n_watched': max_count}


def get_channel_names_from_history(watch_history: list[dict]) -> list:
    """
    Get a list of the channel names of watched videos.

    Args:
        watch_history (list[dict]): A list of dictionaries representing
            a watch history.

    Returns:
        list: A list of the channel names of watched videos.
    """
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


def get_search_term_frequency(
        search_history: list[dict],
        n_terms: int | None = None
) -> list[dict]:
    """
    Get holding information on how often a search term was used.

    Args:
        search_history (list[dict]): List of search history data.
        n_terms (int | None): Number of top search terms to include

    Returns:
        dict: A list of dictionaries representing a search term frequency,
            each containing the keys 'term' and 'count'.
    """
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
