import requests


def get_tiktok_video_metadata(
    video_id: str, session: requests.Session | None = None
) -> dict:
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
    except:  # noqa: E722
        data = {}
    thumbnail = data.get("thumbnail_url")
    channel = data.get("author_name")
    return {"thumbnail": thumbnail, "channel": channel}


def generate_usage_session_image():
    # TODO: Still needs to be implemented
    pass
