from allauth.account.adapter import get_adapter
from allauth.account.forms import LoginForm, RequestLoginCodeForm
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import BaseUserManager
from django.http import HttpResponseRedirect

from mydigitalmeal.profiles.models import MDMProfile

User = get_user_model()


MDM_SETTINGS = settings.ALLAUTH_MDM


class MDMAuthForm(LoginForm):
    """Form for email-based authentication (login/signup)"""

    remember = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("password", None)

    def _clean_without_password(self, email: str | None, phone: None):
        """Handle passwordless authentication.

        Creates users if needed and sends login code.
        """
        if not email:
            self.add_error("login", get_adapter().validation_error("invalid_login"))
            return self.cleaned_data

        self._check_user_exists_or_create_new(email)

        form = RequestLoginCodeForm({"email": email})
        if not form.is_valid():
            for field in ["phone", "email"]:
                errors = form.errors.get(field) or []
                for error in errors:
                    self.add_error("login", error)
        else:
            self.user = getattr(form, "_user", None)

        return self.cleaned_data

    def _check_user_exists_or_create_new(self, email: str) -> None:
        email = BaseUserManager.normalize_email(email)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(email=email, username=email)

        try:
            EmailAddress.objects.get(email=email)
        except EmailAddress.DoesNotExist:
            EmailAddress.objects.create(
                user=user,
                email=email,
            )

        try:
            MDMProfile.objects.get(user=user)
        except MDMProfile.DoesNotExist:
            MDMProfile.objects.create(user=user)

    def _login_by_code(self, request, redirect_url, credentials):
        """Overwrite redirect behaviour of parent class."""
        super()._login_by_code(request, redirect_url, credentials)
        return HttpResponseRedirect(redirect_url)
