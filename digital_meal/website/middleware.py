from django.http import Http404
from django.utils.deprecation import MiddlewareMixin


class RestrictDDMMiddleware(MiddlewareMixin):
    """
    Middleware to restrict access to /ddm/ URLs to staff or superusers only.
    """

    def process_request(self, request):
        if request.path.startswith('/ddm/'):
            if not request.user.is_authenticated:
                raise Http404

            if not (request.user.is_staff or request.user.is_superuser):
                raise Http404

        # Allow the request to proceed normally
        return None
