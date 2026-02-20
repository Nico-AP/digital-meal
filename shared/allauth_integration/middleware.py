from .context import current_request_var
from .settings import AppPrefixes


class SubdomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/my/"):
            request.template_prefix = AppPrefixes.MY_DM.value
        else:
            request.template_prefix = AppPrefixes.DM_EDUCATION.value

        current_request_var.set(request)
        return self.get_response(request)
