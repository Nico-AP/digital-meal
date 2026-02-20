from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

from .context import current_request_var
from .settings import AppPrefixes

MDM_SETTINGS = settings.ALLAUTH_MDM


class SubdomainAccountAdapter(DefaultAccountAdapter):
    def _is_dm_education(self, request):
        return getattr(request, "template_prefix", "") == AppPrefixes.DM_EDUCATION

    def _get_setting(self, key, request=None):
        if request is None:
            request = self._get_request()
        if request and not self._is_dm_education(request):
            return MDM_SETTINGS.get(key, getattr(settings, key, None))
        return getattr(settings, key, None)

    def _get_request(self):
        return current_request_var.get()

    def get_logout_redirect_url(self, request):
        return self._get_setting("ACCOUNT_LOGOUT_REDIRECT_URL", request)

    def format_email_subject(self, subject):
        request = self._get_request()
        prefix = self._get_setting("ACCOUNT_EMAIL_SUBJECT_PREFIX", request)
        return f"{prefix}{subject}"
