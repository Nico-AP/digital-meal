from dateutil.parser import parse


def get_video_ids(watch_history):
    """ Get a list containing only the video ids from the watch history. """
    video_ids = [
        d['Link'].rstrip('/').split('/')[-1]
        for d in watch_history if 'Link' in d
    ]
    return video_ids

def get_date_list(watch_history):
    """ Get a list containing the dates of all watched videos. """
    dates = [parse(d['Date']) for d in watch_history if 'Date' in d]
    return dates

def get_video_metadata(video_id):
    url = 'https://www.tiktok.com/oembed?url=https://www.tiktok.com/@/video/'
    url += (video_id + '/')

    import requests

    response = requests.get(url)
    data = response.json()
    thumbnail = data.get('thumbnail_url', None)
    channel = data.get('author_name', None)
    return {'thumbnail': thumbnail, 'channel': channel}
