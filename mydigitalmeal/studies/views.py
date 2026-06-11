import logging

from ddm.projects.models import DonationProject
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
from mydigitalmeal.datadonation.views.ddm import BaseDonationViewDDM
from mydigitalmeal.studies.sessions import StudyParticipationSessionManager
from mydigitalmeal.userflow.sessions import AddUserflowSessionMixin
from shared.portability import views as port_views

logger = logging.getLogger(__name__)


class StudyEnrollView(View):
    """View to connect participants from external sources to DDM.

    Creates a study participation session entry (StudyParticipationSession)
    and populates it with the information passed through URL parameters.
    After session creation, redirects to the login view.

    All passed URL parameters are extracted and later stored in DDM under
    the participant's url parameter information.
    The following URL parameters are extracted separately and later reused to
    connect to the correct data donation project and donation path:
    - project_id: the URL ID of the DDM project to which to connect; if not
        provided, the default project is used.
    - method: 'papi' if participant should be redirected to the portability
        donation route, 'dua' if participant should be redirected to the
        download-upload route. Defaults to portability route if not provided
        or misspecified.
    """

    def get(self, request, *args, **kwargs):
        # Initialize study participation session
        study_session = StudyParticipationSessionManager.from_request(request)
        study_session.reset()

        # TODO: Participant must be reset here or in DownloadUploadView.

        # Extract URL parameters
        url_parameters = dict(request.GET.items())
        project_id = request.GET.get("project_id", None)
        method = request.GET.get("method", "papi")

        study_session.update(
            url_parameters=url_parameters,
            ddm_project_id=project_id,
            method=method
        )

        if method == "papi":
            return redirect("mdm:userflow:studies:port_tt_connect")
        return redirect("mdm:userflow:studies:download_upload")


class DownloadUploadView(BaseDonationViewDDM):
    """View to connect participants from external sources to DDM."""

    # TODO: Reject requests without study session

    def get_ddm_project(self, request) -> DonationProject:
        """Get DDM project from study participation session or return default."""
        study_session = StudyParticipationSessionManager.from_request(request).get()

        if study_session and study_session.ddm_project_id:
            project = DonationProject.objects.filter(
                url_id=study_session.ddm_project_id).first()
            if project:
                return project

        return DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)

    def update_participant_information(self, request) -> None:
        """Add url parameters to participant information."""
        study_session = StudyParticipationSessionManager.from_request(request).get()

        if study_session:
            self.participant.extra_data["url_param"] = study_session.url_parameters
            enroll_time = study_session.enroll_time.isoformat() \
                if study_session.enroll_time else None
            self.participant.extra_data["enroll_time"] = enroll_time
        self.participant.save()


# PORTABILITY VIEWS
class PortabilityEntryView(port_views.TikTokAuthView):
    template_name = "studies/portability/tiktok_auth.html"


class PortabilityWaitingView(
    AddUserflowSessionMixin,
    port_views.TikTokAwaitDataDownloadView,
):
    template_name = "studies/portability/tiktok_await_download.html"

    def validate_userflow_session(
        self, request, *args, **kwargs
    ) -> HttpResponseRedirect | None:
        """Redirect to report if statistics request ID in session."""
        userflow_session = self.userflow_session.get()
        if getattr(userflow_session, "request_id", None):
            return HttpResponseRedirect(reverse("mdm:userflow:reports:tiktok_report"))  # noqa: F821
        return None


# TODO: Check if can be optimized to reduce redundancies.
class CheckDownloadAvailabilityView(port_views.TikTokCheckDownloadAvailabilityView):
    """Returns appropriate status for the download availability.

    Returns rendered html partial and intended to be called by an HTMX component.
    """

    template_name = None  # Note: is assigned in get_context_data

    template_pending = (
        "studies/portability/await_partials/_data_download_pending_msg.html"
    )
    template_success = (
        "studies/portability/await_partials/_data_download_available_msg.html"
    )
    template_error = (
        "studies/portability/await_partials/_data_download_error_msg.html"
    )
    template_expired = (
        "datadonation/portability/await_partials/_data_download_expired_msg.html"
    )


# TODO: Check if can be optimized to reduce redundancies.
class PortabilityReviewView(
    port_views.AuthenticationRequiredMixin,
    port_views.ActiveAccessTokenRequiredMixin,
    port_views.PortabilitySessionMixin,
    DownloadUploadView,
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
            "mdm:userflow:studies:port_tt_await_data"
        )

        context["portability_view"] = True
        return context
