from django.conf import settings
from django.contrib.auth import get_user_model, logout

from shared.routing.allauth_integration.context import current_request_var
from shared.routing.allauth_integration.sessions import AuthSessionManager
from shared.routing.allauth_integration.settings import AuthContexts
from shared.routing.constants import MDMRoutingTypes

User = get_user_model()


class SubdomainAuthMiddleware:
    """Set template prefix to use for allauth views and auth context in session.

    Requests that fall under MDM are treated as the MY_DM context; all others fall
    into DM_EDUCATION. When a context switch is detected and the current user
    shouldn't persist across it, they are logged out before the request
    continues.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.should_use_mdm_context(request):
            current_ctxt = AuthContexts.MY_DM
            request.template_prefix = AuthContexts.MY_DM

        else:
            current_ctxt = AuthContexts.DM_EDUCATION
            request.template_prefix = AuthContexts.DM_EDUCATION

        session = AuthSessionManager.from_request(request)
        prev_ctxt = session.get_auth_context()

        if self.should_enforce_context_change(prev_ctxt, current_ctxt):
            if self.should_logout_user(request.user):
                logout(request)

        session.update(auth_context=current_ctxt)
        current_request_var.set(request)
        return self.get_response(request)

    def should_use_mdm_context(self, request) -> bool:
        if settings.MDM_ROUTING_TYPE == MDMRoutingTypes.SUBDOMAIN:
            host = request.get_host().split(":")[0].lower()
            return host == settings.MDM_SUBDOMAIN
        if settings.MDM_ROUTING_TYPE == MDMRoutingTypes.URL_PREFIX:
            return request.path.startswith(f"/{settings.MDM_URL_PREFIX}")
        return False

    def should_enforce_context_change(self, prev_context, curr_context) -> bool:
        """Return True if a context switch should trigger re-authentication checks."""
        if not prev_context:
            return False

        if curr_context == AuthContexts.MY_DM:
            return False
        return prev_context != curr_context

    def should_logout_user(self, user: User) -> bool:
        """Return True if the user should be logged out on a context switch."""
        if not user.is_authenticated or user.is_staff:
            return False

        # Check if user has teacher profile
        return not hasattr(user, "teacher")
