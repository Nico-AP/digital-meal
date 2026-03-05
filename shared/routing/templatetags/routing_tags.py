from django import template

from shared.routing.urls import absolute_reverse

register = template.Library()


@register.simple_tag
def absolute_url(viewname: str, *args, **kwargs) -> str:
    """Return the absolute URL of the given viewname.

    (instead of relative path when using standard url tag)
    """
    return absolute_reverse(viewname, *args, **kwargs)
