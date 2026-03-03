from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template import TemplateDoesNotExist
from django.template.loader import get_template

from .context import current_request_var
from .settings import AppPrefixes

MDM_SETTINGS = settings.ALLAUTH_MDM


class SubdomainAccountAdapter(DefaultAccountAdapter):
    def _is_dm_education(self, request):
        return getattr(request, "template_prefix", "") == AppPrefixes.DM_EDUCATION

    def _get_domain_template_prefix(self, request):
        return getattr(request, "template_prefix", "")

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

    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        """Override parent method to dynamically choose template based on domain."""
        request = self._get_request()
        ctx = {
            "request": request,
            "email": email,
            "current_site": get_current_site(request),
        }
        ctx.update(context)

        # Pick subdomain-specific template if exists
        domain_prefix = self._get_domain_template_prefix(request)
        if domain_prefix:
            try:
                template_name = f"{domain_prefix}/{template_prefix}_message.txt"
                get_template(template_name)
                template_prefix = f"{domain_prefix}/{template_prefix}"
            except TemplateDoesNotExist:
                pass

        msg = self.render_mail(template_prefix, email, ctx)
        msg.send()
