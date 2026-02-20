from django.views.generic import TemplateView

from shared.portability import views as port_views


class PortabilityEntryView(port_views.TikTokAuthView):
    template_name = "datadonation/portability/tiktok_auth.html"


# TODO: Inherit correct view when working
class PortabilityWaitingView(
    port_views.PortabilitySessionMixin,
    TemplateView,
):
    template_name = "datadonation/portability/tiktok_await_download.html"


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


class PortabilityReviewView(port_views.TikTokDataReviewView):
    template_name = "portability/tiktok_data_review.html"
