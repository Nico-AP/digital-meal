from functools import wraps

from allauth.account.adapter import get_adapter
from allauth.account.internal import flows
from allauth.account.internal.decorators import login_not_required
from allauth.account.stages import LoginByCodeStage, LoginStageController
from allauth.account.views import ConfirmLoginCodeView, LoginView, LogoutView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from mydigitalmeal.profiles.forms import MDMAuthForm
from mydigitalmeal.userflow.constants import URLShortcut

User = get_user_model()


class MDMAuthView(LoginView):
    """View to sign up or log in."""

    form_class = MDMAuthForm
    template_name = "profiles/login.html"

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)

        # Intercept default allauth redirection.
        if isinstance(result, HttpResponseRedirect):
            allauth_confirm_url = reverse("account_confirm_login_code")
            if result.url == allauth_confirm_url:
                actual_confirm_url = reverse(URLShortcut.CONFIRM_LOGIN)
                return HttpResponseRedirect(actual_confirm_url)

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["passwordless_enabled"] = True
        context["request_login_code_url"] = reverse(URLShortcut.CONFIRM_LOGIN)
        context["LOGIN_BY_CODE_ENABLED"] = True
        return context

    def get_success_url(self):
        return reverse(URLShortcut.CONFIRM_LOGIN)

    def get_authenticated_redirect_url(self):
        # TODO: Later maybe redirect to report, if user has already donated
        return reverse(URLShortcut.OVERVIEW)


def login_stage_required_custom(stage: str, redirect_urlname: str):
    """Overwrite decorator to redirect authenticated user to donation"""

    def decorator(view_func):
        @never_cache
        @login_not_required
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                # TODO: Later maybe redirect to report, if user has already donated
                return HttpResponseRedirect(reverse(URLShortcut.OVERVIEW))
            login_stage = LoginStageController.enter(request, stage)
            if not login_stage:
                return HttpResponseRedirect(reverse(redirect_urlname))
            request._login_stage = login_stage  # noqa: SLF001
            return view_func(request, *args, **kwargs)

        return _wrapper_view

    return decorator


@method_decorator(
    login_stage_required_custom(
        stage=LoginByCodeStage.key,
        redirect_urlname=URLShortcut.LOGIN,
    ),
    name="dispatch",
)
class MDMConfirmLoginCodeView(ConfirmLoginCodeView):
    template_name = "profiles/confirm_login_code.html"

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        """Override to route to My Digital Meal login view when stage not set."""
        self.stage = request._login_stage  # noqa: SLF001
        self._process = flows.login_by_code.LoginCodeVerificationProcess.resume(
            self.stage
        )
        if not self._process:
            return HttpResponseRedirect(reverse("userflow:profiles:auth"))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Activate MDM Profile."""
        _ = super().form_valid(form)

        if hasattr(self.request.user, "mdm_profile"):
            self.request.user.mdm_profile.activate()

        # Redirect to custom target
        return HttpResponseRedirect(self.get_next_url())

    def form_invalid(self, form):
        """Copied from parent class to set different redirect target"""
        attempts_left = self._process.record_invalid_attempt()
        if attempts_left:
            return super().form_invalid(form)
        adapter = get_adapter(self.request)
        adapter.add_message(
            self.request,
            messages.ERROR,
            message=adapter.error_messages["too_many_login_attempts"],
        )

        # Changed to custom view.
        return HttpResponseRedirect(reverse(URLShortcut.LOGIN))

    def get_next_url(self):
        """Redirect to donation step."""
        return reverse(URLShortcut.OVERVIEW)


class MDMLogoutView(LogoutView):
    template_name = "profiles/logout.html"
