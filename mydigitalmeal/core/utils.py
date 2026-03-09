from urllib.parse import urlparse


def to_relative_url(url):
    """Converts an url to a relative url."""
    parsed = urlparse(url)
    relative = parsed.path
    if parsed.query:
        relative += "?" + parsed.query
    if parsed.fragment:
        relative += "#" + parsed.fragment
    return relative
