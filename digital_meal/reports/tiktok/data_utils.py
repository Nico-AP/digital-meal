import pandas as pd
import requests


def get_video_ids(watch_history):
    """ Get a list containing only the video ids from the watch history. """
    video_ids = []
    for d in watch_history:
        if 'Link' in d:
            link_parts = d['Link'].split('/')
            # Get last non-empty part
            video_id = link_parts[-1] if link_parts[-1] else link_parts[-2]
            video_ids.append(video_id)
    return video_ids

def get_date_list(watch_history):
    """ Get a list containing the dates of all watched videos. """
    dates_str = [d['Date'] for d in watch_history if 'Date' in d]
    if not dates_str:
        return []

    dates = pd.to_datetime(dates_str, errors='coerce').dropna().tolist()
    return dates

def get_video_metadata(
        video_id,
        session: requests.Session | None = None
) -> dict:
    """ Get TikTok video metadata from official embed API. """
    if session is None:
        session = requests.Session()

    url = f'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@/video/{video_id}/'

    try:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
    except:
        data = {}
    thumbnail = data.get('thumbnail_url', None)
    channel = data.get('author_name', None)
    return {'thumbnail': thumbnail, 'channel': channel}
