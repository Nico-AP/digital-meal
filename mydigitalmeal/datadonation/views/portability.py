from django.http import HttpResponseRedirect
from django.urls import reverse

from mydigitalmeal.datadonation.views.ddm import DonationViewDDM
from mydigitalmeal.userflow.sessions import AddUserflowSessionMixin
from shared.portability import views as port_views


class PortabilityEntryView(port_views.TikTokAuthView):
    template_name = "datadonation/portability/tiktok_auth.html"


class PortabilityWaitingView(
    AddUserflowSessionMixin,
    port_views.TikTokAwaitDataDownloadView,
):
    # Note: For testing purposes, view can inherit (circumvents portability session
    # authentication):
    # from django.views.generic import TemplateView  # noqa: ERA001
    # port_views.PortabilitySessionMixin,
    # TemplateView,

    template_name = "datadonation/portability/tiktok_await_download.html"

    def validate_userflow_session(
        self, request, *args, **kwargs
    ) -> HttpResponseRedirect | None:
        """Redirect to report if statistics request ID in session."""
        userflow_session = self.userflow_session.get()
        if userflow_session.request_id:
            return HttpResponseRedirect(reverse("userflow:reports:tiktok_report"))
        return None


class CheckDownloadAvailabilityView(port_views.TikTokCheckDownloadAvailabilityView):
    """Returns appropriate status for the download availability.

    Returns rendered html partial and intended to be called by an HTMX component.
    """

    template_name = None  # Note: is assigned in get_context_data

    template_pending = (
        "datadonation/portability/await_partials/_data_download_pending_msg.html"
    )
    template_success = (
        "datadonation/portability/await_partials/_data_download_available_msg.html"
    )
    template_error = (
        "datadonation/portability/await_partials/_data_download_error_msg.html"
    )
    template_expired = (
        "datadonation/portability/await_partials/_data_download_expired_msg.html"
    )


class PortabilityReviewView(
    port_views.AuthenticationRequiredMixin,
    port_views.ActiveAccessTokenRequiredMixin,
    port_views.PortabilitySessionMixin,
    DonationViewDDM,
):
    template_name = "datadonation/portability/tiktok_review.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        mock_download = False  # Note: Can be set to True for testing purposes
        if mock_download:
            download_url = reverse("tiktok_download_mock_data")
        else:
            download_url = reverse("tiktok_download_data")

        context["tiktok_download_url"] = download_url
        context["fail_redirect_url"] = reverse(
            "userflow:datadonation:port_tt_await_data"
        )

        context["portability_view"] = True
        return context
