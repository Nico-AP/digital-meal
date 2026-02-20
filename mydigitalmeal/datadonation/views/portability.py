from shared.portability import views as port_views


class PortabilityEntryView(port_views.TikTokAuthView):
    template_name = "datadonation/portability/tiktok_auth.html"


class PortabilityWaitingView(port_views.TikTokAwaitDataDownloadView):
    template_name = "datadonation/portability/tiktok_await_download.html"


class PortabilityReviewView(port_views.TikTokDataReviewView):
    template_name = "portability/tiktok_data_review.html"
