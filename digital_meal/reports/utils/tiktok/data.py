import datetime
from typing import TypedDict

import pandas as pd
import requests


def _get_first_matching_key(entry: dict, possible_keys: list[str]) -> str | None:
    """Return the first of the possible_keys that is present in entry."""
    for key in possible_keys:
        if key in entry:
            return key
    return None


class WatchHistoryData(TypedDict):
    videos: list[dict]
    video_ids: list[str]
    video_dates: list[datetime.datetime]
    videos_separate: list[list[dict]]
    video_ids_separate: list[list[str]] | None
    video_dates_separate: list[list[datetime.datetime]] | None
    n_participants: int


def extract_watch_history_data(
    watch_histories: list[list[dict]],
    keep_separate: bool = False,  # noqa: FBT002
) -> WatchHistoryData:
    """Create a WatchHistoryData object from a list of watch histories.

    Iterates over the watch histories to extract the following information:

    - List of video IDs
    - List of video dates in datetime.datetime format
    - On how many participants the data is based

    If keep_separate is True, the information is additionally kept separate for
    each individual.

    Args:
        watch_histories: A list of YouTube watch histories.
        keep_separate: A boolean indicating whether to keep information on
            separate watch histories.

    Returns:
        dict: A tiktok.WatchHistoryData object
    """
    videos_combined = []
    video_ids_combined = []
    video_dates_combined = []

    videos_separate = [] if keep_separate else None
    video_ids_separate = [] if keep_separate else None
    video_dates_separate = [] if keep_separate else None

    for history in watch_histories:
        videos = []
        video_ids = []
        video_dates = []

        for entry in history:
            video_id = get_video_id(entry)
            entry["id"] = video_id
            if video_id is not None:
                video_ids.append(video_id)

            video_date = get_watch_date(entry)
            entry["date"] = video_date
            if video_date is not None:
                video_dates.append(video_date)

            if video_date is not None or video_id is not None:
                videos.append(entry)

        video_dates = (
            pd.to_datetime(video_dates, errors="coerce", utc=True, format="mixed")
            .dropna()
            .tolist()
        )

        if keep_separate:
            videos_separate.append(videos)
            video_ids_separate.append(video_ids)
            video_dates_separate.append(video_dates)

        videos_combined.extend(videos)
        video_ids_combined.extend(video_ids)
        video_dates_combined.extend(video_dates)

    n_participants = len(watch_histories)

    return WatchHistoryData(
        videos=videos_combined,
        video_ids=video_ids_combined,
        video_dates=video_dates_combined,
        videos_separate=videos_separate,
        video_ids_separate=video_ids_separate,
        video_dates_separate=video_dates_separate,
        n_participants=n_participants,
    )


class SearchHistoryData(TypedDict):
    searches: list[dict]
    search_terms: list[str]
    search_terms_separate: list[list[str]] | None
    n_participants: int


def _get_search_term_key(search_entry: dict) -> str | None:
    possible_keys = [
        "SearchTerm",
        "searchterm",
        "search_term",
    ]
    return _get_first_matching_key(search_entry, possible_keys)


def extract_search_history_data(
    search_histories: list[list[dict]],
    keep_separate: bool = False,  # noqa: FBT002
) -> SearchHistoryData:
    """Create a SearchHistoryData object from a list of search histories.

    Iterates over the search histories, excludes ads from the histories and
    extracts the following information:

    - List of search entries
    - List of search terms
    - On how many participants the data is based

    If keep_separate is True, the list of search terms is additionally kept
    separate for each individual.

    Args:
        search_histories: A list of YouTube search histories.
        keep_separate: A boolean indicating whether to keep information on
            separate search histories.

    Returns:
        dict: A SearchHistoryData object
    """

    searches_combined = []
    search_terms_combined = []

    search_term_separate = [] if keep_separate else None

    for history in search_histories:
        searches = []
        search_terms = []

        for entry in history:
            search_key = _get_search_term_key(entry)
            if search_key is None:
                continue

            # Clean search title
            title = entry.get(search_key)
            if title is None:
                continue

            date_key = _get_date_key(entry)
            if date_key is not None:
                entry["date"] = entry[date_key]

            searches.append(entry)
            search_terms.append(title)

        if keep_separate:
            search_term_separate.append(search_terms)

        searches_combined.extend(searches)
        search_terms_combined.extend(search_terms)

    n_participants = len(search_histories)

    return {
        "searches": searches_combined,
        "search_terms": search_terms_combined,
        "search_terms_separate": search_term_separate,
        "n_participants": n_participants,
    }


def _get_link_key(watch_entry: dict) -> str | None:
    possible_keys = [
        "(L|l)ink",
        "Link",
        "link",
    ]
    return _get_first_matching_key(watch_entry, possible_keys)


def get_video_id(watch_entry: dict) -> str | None:
    """Get the video id from a watch history entry."""
    link_key = _get_link_key(watch_entry)
    if link_key is None:
        return None

    link_parts = watch_entry[link_key].split("/")
    # Get last non-empty part
    video_id = link_parts[-1] if link_parts[-1] else link_parts[-2]
    return video_id


def _get_date_key(watch_entry: dict) -> str | None:
    possible_keys = [
        "(D|d)ate",
        "Date",
        "date",
    ]
    return _get_first_matching_key(watch_entry, possible_keys)


def get_watch_date(watch_entry: dict) -> str | None:
    """Get the watch date from a watch history entry."""
    date_key = _get_date_key(watch_entry)
    if date_key is None:
        return None

    date_str = watch_entry[date_key]
    return date_str


def get_video_metadata(video_id: str, session: requests.Session | None = None) -> dict:
    """Get TikTok video metadata from official embed API."""
    if session is None:
        session = requests.Session()

    url = (
        f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@/video/{video_id}/"
    )

    try:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
    except:  # noqa: E722 TODO
        data = {}
    thumbnail = data.get("thumbnail_url", None)
    channel = data.get("author_name", None)
    return {"thumbnail": thumbnail, "channel": channel}
