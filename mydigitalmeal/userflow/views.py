import logging

from ddm.participation.views import (
    create_participation_session,
    get_participation_session_id,
)
from ddm.projects.models import DonationProject
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG, DonationMethod
from mydigitalmeal.profiles.mixins import LoginAndProfileRequiredMixin
from mydigitalmeal.profiles.models import MDMProfile
from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.studies.sessions import StudyParticipationSessionManager
from mydigitalmeal.userflow.constants import URLShortcut
from mydigitalmeal.userflow.sessions import AddUserflowSessionMixin

logger = logging.getLogger(__name__)


class LandingPageView(TemplateView):
    template_name = "userflow/landing_page.html"


class OverviewView(LoginAndProfileRequiredMixin, AddUserflowSessionMixin, TemplateView):
    template_name = "userflow/overview.html"
    login_url = reverse_lazy(URLShortcut.LOGIN)

    def get(self, request, *args, **kwargs):
        # TODO: Set up redirect when tested
        # profile = self.get_user_profile()  # noqa: ERA001
        # n_stats_requests = StatisticsRequest.objects.filter(profile=profile).count()  # noqa: ERA001, E501
        # if n_stats_requests == 0:
        #     return redirect(URLShortcut.DONATION_DDM)  # noqa: ERA001

        return super().get(request, *args, **kwargs)

    def get_user_profile(self):
        user = self.request.user
        return MDMProfile.objects.get(user=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["requests"] = StatisticsRequest.objects.filter(
            profile=self.get_user_profile(),
            status=StatisticsRequest.States.SUCCESS,
            tiktok_wh_statistics__scope=StatisticsScope.INTERVAL,
        )
        return context


class UserflowResumeView(LoginAndProfileRequiredMixin, AddUserflowSessionMixin, View):
    """View to redirect user to a specific statistics request.

    Sets the session values in MDM and DDM sessions to the appropriate values.
    """

    def get(self, request, *args, **kwargs):
        profile = self.get_mdm_profile()

        request_id = self.kwargs.get("request_id")
        if request_id is None:
            return redirect(URLShortcut.OVERVIEW)

        try:
            stats_request = StatisticsRequest.objects.get(public_id=request_id)
        except StatisticsRequest.DoesNotExist:
            msg = (
                "Registered attempt to resume non-existent request "
                f"(request ID: {request_id}; profile: {profile.id})"
            )
            logger.warning(msg)
            return redirect(URLShortcut.OVERVIEW)

        if stats_request.profile != profile:
            msg = (
                f"Profile tried to access statistics request belonging to "
                f"different user. "
                f"(request: {stats_request.id}; profile: {profile.id}; "
                f"request owner: {stats_request.profile.id})"
            )
            logger.warning(msg)
            return redirect(URLShortcut.OVERVIEW)

        self.update_participant_in_session(stats_request)
        self.userflow_session.update(
            statistics_requested=True,
            request_id=stats_request.public_id,
        )
        return redirect(URLShortcut.DONATION_DDM)

    def get_mdm_profile(self):
        return MDMProfile.objects.get(user=self.request.user)

    def get_donation_project(self):
        try:
            project = DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)
        except DonationProject.DoesNotExist as e:
            raise Http404 from e
        return project

    def update_participant_in_session(self, stats_request: StatisticsRequest):
        project = self.get_donation_project()
        participant = stats_request.participant
        create_participation_session(self.request, project)  # Does nothing if existing
        session_id = get_participation_session_id(project)
        self.request.session[session_id]["participant_id"] = participant.id
        self.request.session.modified = True


class UserflowResetView(LoginAndProfileRequiredMixin, AddUserflowSessionMixin, View):
    """View to prepare a new specific statistics request.

    Resets the session values in MDM and DDM sessions.
    """

    def get(self, request, *args, **kwargs):
        self.reset_participant_in_session()
        self.userflow_session.reset()

        method = request.GET.get("method", DonationMethod.DOWNLOAD_UPLOAD)
        if method == DonationMethod.PORTABILITY:
            return redirect(URLShortcut.DONATION_PORTABILITY)
        return redirect(URLShortcut.DONATION_DDM)

    def get_donation_project(self):
        try:
            project = DonationProject.objects.get(slug=TIKTOK_PROJECT_SLUG)
        except DonationProject.DoesNotExist as e:
            msg = "Required DDM project could not be found."
            raise Http404(msg) from e
        return project

    def reset_participant_in_session(self):
        project = self.get_donation_project()
        session_id = get_participation_session_id(project)
        self.request.session[session_id] = {}
        self.request.session.modified = True


def _study_flow_is_active(request) -> bool:
    """True if the current browser session is mid-study-flow.

    Used by the portability routers to decide whether to send
    OAuth-callback / auth-retry traffic into the studies flow or fall
    through to the regular MDM path. ``completed`` is flipped to True by
    ``StudyDebriefingView`` once the participant has rendered the
    debriefing page, so post-debriefing traffic falls through.
    """
    study_session = StudyParticipationSessionManager.from_request(request).get()
    return bool(
        study_session and study_session.ddm_project_id and not study_session.completed,
    )


class PortabilityCallbackRouterView(View):
    """Routes the post-OAuth participant to the correct await view.

    Studies participants in an active flow go to the studies await page;
    completed or non-study participants fall through to the regular MDM
    datadonation await page.
    """

    def get(self, request, *args, **kwargs):
        if _study_flow_is_active(request):
            logger.debug("Portability callback routed to studies flow.")
            return redirect("mdm:userflow:studies:port_tt_await_data")
        logger.debug("Portability callback routed to datadonation flow.")
        return redirect("mdm:userflow:datadonation:port_tt_await_data")


class PortabilityAuthRetryRouterView(View):
    """Routes auth view redirections to the correct entry view.

    Studies participants in an active flow go to the studies connect
    page; completed or non-study participants fall through to the
    regular MDM connect page.
    """

    def get(self, request, *args, **kwargs):
        if _study_flow_is_active(request):
            logger.debug("Portability auth retry routed to studies flow.")
            return redirect("mdm:userflow:studies:port_tt_connect")
        logger.debug("Portability auth retry routed to datadonation flow.")
        return redirect("mdm:userflow:datadonation:port_tt_connect")


class PortabilityAbortRouterView(View):
    """Routes users who aborted the portability flow to the correct entry view.

    Studies participants in an active flow go to the studies abort page;
    completed or non-study participants fall through to the
    regular MDM connect page.
    """

    def get(self, request, *args, **kwargs):
        if _study_flow_is_active(request):
            logger.debug("Portability abort routed to studies flow.")
            return redirect("mdm:userflow:studies:port_tt_aborted")
        logger.debug("Portability abort routed to datadonation flow.")
        return redirect("mdm:userflow:datadonation:port_tt_aborted")


class PortabilityFailedRouterView(View):
    """Routes users who experienced a failure in the portability flow to the
    correct entry view.

    Studies participants in an active flow go to the studies failure page;
    completed or non-study participants fall through to the
    regular MDM connect page.
    """

    def get(self, request, *args, **kwargs):
        if _study_flow_is_active(request):
            logger.debug("Portability failed routed to studies flow.")
            return redirect("mdm:userflow:studies:port_tt_failed")
        logger.debug("Portability failed routed to datadonation flow.")
        # TODO: At some point we may want to add an extra view for this
        return redirect("mdm:userflow:datadonation:port_tt_connect")
