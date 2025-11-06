import datetime
from typing import TypedDict

import pandas as pd
import random
import re


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
    dates_str = [d['time'] for d in watch_history if 'time' in d]
    if not dates_str:
        return []

    dates = pd.to_datetime(dates_str, errors='coerce').dropna().tolist()
    return dates


def get_title_list(history: list[dict]) -> list:
    """
    Extracts the 'title' from a list of watch/search history events.

    Args:
        history: A list of history events dictionaries.

    Returns:
        list: A list of search terms.
    """
    titles = [
        event['title']
        for event in history
        if 'title' in event and event['title']
    ]
    return titles


def is_ad(watch_entry: dict) -> bool:
    """
    Checks if a watch entry is an ad.

    Args:
        watch_entry: Watch entry dictionary.

    Returns:
        bool: True if it is an ad, False otherwise.
    """
    ad_identifiers = {
        'from google ads',
        'von google anzeigen',
        'da programmi pubblicitari google',
        'des annonces google',
    }

    entry_is_ad = (
        'details' in watch_entry
        and len(watch_entry['details']) > 0
        and 'name' in watch_entry['details'][0]
        and watch_entry['details'][0]['name'].lower() in ad_identifiers
    )
    return entry_is_ad


def get_video_id(watch_entry: dict) -> str | None:
    """
    Extract the video ID from a watch entry.

    Args:
        watch_entry: Watch entry dictionary.

    Returns:
        str: The video ID if it is contained in the entry, None otherwise.
    """
    title_url = watch_entry.get('titleUrl')

    if title_url:
        return title_url.replace('https://www.youtube.com/watch?v=', '')
    else:
        return None


def convert_date_strings_to_datetime(
        date_strings: list[str]
) -> list[datetime.datetime]:
    """
    Convert a list of date strings into a list of datetime objects.

    Args:
        date_strings: List of dates as strings.

    Returns:
        list[datetime.datetime]: List of datetime objects.
    """
    return pd.to_datetime(date_strings, errors='coerce').dropna().tolist()


def get_channel_name(watch_entry: dict) -> str | None:
    """
    Extract the channels name from a watch entry.

    Args:
        watch_entry: Watch entry dictionary.

    Returns:
        str: The channel name. None if this information is missing.
    """
    subtitles = watch_entry.get('subtitles')

    if subtitles is None:
        return None

    if len(subtitles) > 0:
        if 'name' in subtitles[0]:
            return subtitles[0]['name']

    return None


class WatchHistoryData(TypedDict):
    without_ads: list[dict]
    video_ids: list[str]
    video_dates: list[datetime.datetime]
    channels: list[str]


def extract_watch_history_data(watch_history: list[dict]) -> WatchHistoryData:
    """
    Iterates once over the watch history to extract the following information:

    - Clean watch history without ads
    - List of video IDs
    - List of video dates in datetime.datetime format
    - List of channel names

    Args:
        watch_history: A YouTube watch history.

    Returns:
        dict: Returns a dictionary that contains this data in the following
            keys: 'without_ads', 'video_ids', 'video_dates', 'channels'.
    """
    no_ads = []
    ids = []
    dates = []
    channels = []

    for entry in watch_history:
        # Check if it is an ad
        if is_ad(entry):
            continue

        no_ads.append(entry)

        # Extract video id and title
        video_id = get_video_id(entry)
        if video_id is not None:
            ids.append(video_id)

        # Extract video date
        video_date = entry.get('time')
        if video_date is not None:
            dates.append(video_date)

        # Extract channel
        channel = get_channel_name(entry)
        if channel is not None:
            channels.append(channel)

    # Convert date strings to datetime objects
    dates = convert_date_strings_to_datetime(dates)

    return {
        'without_ads': no_ads,
        'video_ids': ids,
        'video_dates': dates,
        'channels': channels,
    }


def is_search_ad(search_entry: dict) -> bool:
    """
    Checks if a search entry is an ad.

    Args:
        search_entry: Search entry dictionary.

    Returns:
        bool: True if it is an ad, False otherwise.
    """
    ad_identifiers = {
        'web & app activity',
        'web- & app-aktivitäten',
        'attività web e app',
        'activité sur le web et les applications'
    }

    if 'activityControls' in search_entry:
        if any(item.lower() in ad_identifiers
               for item in search_entry['activityControls']):
            return True

    return False


class SearchHistoryData(TypedDict):
    without_ads: list[dict]
    search_terms: list[str]


def extract_search_history_data(search_history: list[dict]) -> SearchHistoryData:
    """
    Iterates once over the search history to extract the following information:

    - Clean search history to exclude ads
    - List of search terms

    Args:
        search_history: A YouTube search history.

    Returns:
        dict: Returns a dictionary that contains this data in the following
            keys: 'without_ads', 'search_terms'.
    """

    no_ads = []
    search_terms = []
    for entry in search_history:
        if is_search_ad(entry):
            continue

        # Clean search title
        title = entry.get('title')
        if title is not None:
            clean_title = clean_search_title(title)
            entry['title'] = clean_title

            if clean_title:
                search_terms.append(clean_title)

        no_ads.append(entry)

    return {
        'without_ads': no_ads,
        'search_terms': search_terms,
    }


def exclude_google_ads_videos(watch_history: list[dict]) -> list[dict]:
    """
    Excludes all videos shown through Google Ads from the watch history.

    Args:
        watch_history (list[dict]): List of watch history data.

    Returns:
        list[dict]: The watch history excluding videos shown through Google Ads.
    """
    ad_identifiers = {
        'from google ads',
        'von google anzeigen',
        'da programmi pubblicitari google',
        'des annonces google',
    }

    watched_videos = []
    for video in watch_history:
        is_ad = (
            'details' in video
            and len(video['details']) > 0
            and 'name' in video['details'][0]
            and video['details'][0]['name'].lower() in ad_identifiers
        )

        if not is_ad:
            watched_videos.append(video)

    return watched_videos


def exclude_ads_from_search_history(search_history: list[dict]) -> list[dict]:
    """
    Excludes all ads from search history.

    Args:
        search_history (list[dict]): List of search history data.

    Returns:
        list[dict]: The search history excluding videos shown through Google Ads.
    """
    ad_identifiers = {
        'web & app activity',
        'web- & app-aktivitäten',
        'attività web e app',
        'activité sur le web et les applications'
    }

    history = [
        entry for entry in search_history
        if 'activityControls' in entry
        and not any(item.lower() in ad_identifiers for item in entry['activityControls'])
    ]
    return history


# Compile regex once at module level for reuse
_SEARCH_PREFIX_PATTERN = re.compile(
    r'^Searched for |^Gesucht nach: |^Hai cercato |^Vous avez recherché '
)


def clean_search_title(search_title: str) -> str:
    """
    Delete pre- and postfixes from search title.
    Supports takeouts in German, English, Italian, and French.

    Args:
        search_title: List of search history data.

    Returns:
        list: The search history with cleaned titles.
    """
    return _SEARCH_PREFIX_PATTERN.sub('', search_title)


def clean_search_titles(search_history: list[dict]) -> list[dict]:
    """
    Delete pre- and postfixes from search titles.
    Supports takeouts in German, English, Italian, and French.

    Args:
        search_history (list): List of search history data.

    Returns:
        list: The search history with cleaned titles.
    """
    clean_searches = []
    for entry in search_history:
        if 'title' in entry:
            entry = entry.copy()
            entry['title'] = _SEARCH_PREFIX_PATTERN.sub('', entry['title'])
        clean_searches.append(entry)

    return clean_searches


# Compile regex once at module level for reuse
_VIDEO_TITLE_PATTERN = re.compile(
    r'^Watched |^Hai guardato |^Vous avez regardé | angesehen$'
)


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
    return _VIDEO_TITLE_PATTERN.sub('', video_title)


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
    # TODO: Make sure, the chosen favorite video is still available, i.e. has not been deleted.

    video_counts = video_ids.value_counts()
    max_count = video_counts.max()

    most_watched_ids = video_counts[video_counts == max_count]
    favorite_video = random.choice(most_watched_ids.index.to_list())
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
    term_counts = search_terms.value_counts()

    if n_terms and len(term_counts) > n_terms:
        term_counts = term_counts[:n_terms]

    searches = [
        {'term': term, 'count': count}
        for term, count in term_counts.items()
    ]
    return searches


def clean_channel_list(channel_list):
    """
    Cleans and standardizes a list of channel dictionaries by
    renaming keys.

    Args:
        channel_list (list): A list of dictionaries, each
        representing a channel.

    Returns:
        list: A new list of dictionaries with standardized keys.
    """
    ddm_id_key = 'Channel ID|Kanal-ID|ID des cha.*|ID canale'
    ddm_title_key = (
        'Channel title|Kanaltitel|Titres des cha.*|Titolo canale'
    )
    keys = {
        f'{ddm_id_key}': 'id',
        f'{ddm_title_key}': 'title',
    }
    channels = []
    for channel in channel_list:
        for key, value in keys.items():
            channel[value] = channel.pop(key, None)
        channels.append(channel)
    return channels
