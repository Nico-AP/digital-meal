import logging
import re
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from ddm.core.utils.user_content.template import render_user_content
from ddm.datadonation.models import FileUploader
from ddm.participation.models import Participant
from ddm.participation.services import UploaderConfigService
from ddm.participation.views import (
    DebriefingView,
    QuestionnaireView,
    create_participation_session,
    get_participation_session_id,
)
from ddm.projects.models import DonationProject
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from mydigitalmeal.datadonation.constants import DonationMethod
from mydigitalmeal.datadonation.utils import get_current_step_url, get_next_step_url
from mydigitalmeal.datadonation.views.ddm import BaseDonationViewDDM
from mydigitalmeal.reports.views.tiktok import BaseStatisticsView
from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.studies.constants import (
    SECONDS_TO_REMINDER,
    TRAIL_KEY,
    DLULTrailSteps,
    PAPITrailSteps,
    StudiesURLShortcut,
    get_dlul_trail,
    get_papi_trail,
)
from mydigitalmeal.studies.exceptions import (
    ProjectInactiveError,
    ProjectNotRegisteredAsStudyError,
    StudyProjectNotFoundError,
)
from mydigitalmeal.studies.sessions import (
    StudyParticipationSession,
    StudyParticipationSessionManager,
)
from mydigitalmeal.userflow.constants import URLShortcut
from mydigitalmeal.userflow.sessions import (
    AddUserflowSessionMixin,
    UserflowSessionManager,
)
from shared.portability import views as port_views
from shared.portability.models import TikTokDataRequest

logger = logging.getLogger(__name__)

# Persisted-URL-parameter shape constraints. The enrollment endpoint accepts
# arbitrary query strings from an external survey tool; these caps bound how
# much of that input we are willing to keep in the session and replay into
# the DDM Participant's extra_data JSON column.
MAX_URL_PARAM_KEYS = 20
MAX_URL_PARAM_VALUE_LENGTH = 200
MAX_URL_PARAM_TOTAL_BYTES = 4096
_URL_PARAM_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{1,40}$")
_RESERVED_URL_PARAMS = frozenset({"project_id", "method"})

_STUDIES_FLOW_STEPS = [
    URLShortcut.OVERVIEW,
    StudiesURLShortcut.DONATION_DDM,
    StudiesURLShortcut.QUESTIONNAIRE,
    StudiesURLShortcut.DEBRIEFING,
]


def _sanitize_url_parameters(query) -> dict:
    """Filter a QueryDict down to values safe to persist on the participant.

    Enforces a key allowlist regex, truncates values, and stops once total size or key
    count is exceeded. Multi-valued params are preserved as lists.
    """
    sanitized: dict[str, str | list[str]] = {}
    running_size = 0
    for key, values in query.lists():
        if not _URL_PARAM_KEY_RE.match(key):
            continue
        if len(sanitized) >= MAX_URL_PARAM_KEYS:
            break

        truncated = [str(v)[:MAX_URL_PARAM_VALUE_LENGTH] for v in values]
        running_size += len(key) + sum(len(v) for v in truncated)
        if running_size > MAX_URL_PARAM_TOTAL_BYTES:
            break

        sanitized[key] = truncated[0] if len(truncated) == 1 else truncated
    return sanitized


def get_participant_from_session(
    request: HttpRequest, project: DonationProject
) -> Participant:
    """Gets/creates participant from session."""
    session_id = get_participation_session_id(project)
    participant_id = request.session[session_id]["participant_id"]
    try:
        participant = Participant.objects.get(pk=participant_id)
    except Participant.DoesNotExist:
        participant = Participant.objects.create(
            project=project, start_time=timezone.now()
        )
        request.session[session_id]["participant_id"] = participant.id
        request.session.modified = True
    return participant


def update_participant_trail(
    participant: Participant,
    key: str,
    only_add_if_empty: bool = False,  # noqa: FBT002
) -> None:
    """Updates the participation trail stored in
    participant.extra_data["participation_trail"]."""
    if TRAIL_KEY not in participant.extra_data:
        participant.extra_data[TRAIL_KEY] = {}

    trail = participant.extra_data[TRAIL_KEY]
    if key not in trail:
        trail[key] = []

    if only_add_if_empty and len(trail[key]) > 0:
        return

    trail[key].append(timezone.now().isoformat())
    participant.save(update_fields=["extra_data"])


class StudyEnrollView(View):
    """Entry point for external survey-tool redirects into the study flow.

    Threat model: this is an unauthenticated GET with session side-effects;
    request authenticity is not verified at this layer. To bound the blast
    radius the view (a) only enrolls into DDM projects that already exist
    and returns 404 otherwise, (b) drops persisted URL parameters that do
    not match a key allowlist, (c) caps the number, length, and total size
    of persisted parameters, and (d) coerces ``method`` to a known value.

    URL parameters:
        project_id: DDM project ``url_id`` to enroll into. Required;
            requests without a ``project_id`` are rejected with 404.
        method: One of `DonationMethod` values. Defaults to
            ``DonationMethod.PORTABILITY``; unknown values are coerced to
            the default.
        <other>: any additional URL parameters are filtered through
            `_sanitize_url_parameters` and replayed onto the DDM
            ``Participant.extra_data`` later in the flow.
    """

    def get(self, request: HttpRequest, *args, **kwargs):
        study_session = StudyParticipationSessionManager.from_request(request)
        study_session.reset()

        project_id, method = self._parse_params(request)
        project = self._get_registered_project(project_id)

        UserflowSessionManager.from_request(request).reset()
        self._reset_ddm_session(request, project)

        url_params = _sanitize_url_parameters(request.GET)
        study_session.update(
            url_parameters=url_params,
            ddm_project_id=project.url_id,
            method=method,
            enroll_time=timezone.now(),
        )

        participant = self._enroll_participant(request, project, method, url_params)
        if method == DonationMethod.PORTABILITY.value:
            update_participant_trail(participant, PAPITrailSteps.ENROLLED)
        else:
            update_participant_trail(participant, DLULTrailSteps.ENROLLED)
        participant.save()

        if method == DonationMethod.PORTABILITY.value:
            return redirect(StudiesURLShortcut.DONATION_PORTABILITY)
        return redirect(StudiesURLShortcut.DONATION_DDM)

    @staticmethod
    def _parse_params(request: HttpRequest) -> tuple:
        project_id = request.GET.get("project_id") or None
        method = request.GET.get("method") or DonationMethod.PORTABILITY.value
        if method not in {m.value for m in DonationMethod}:
            method = DonationMethod.PORTABILITY.value
        return project_id, method

    @staticmethod
    def _get_registered_project(project_id) -> DonationProject:
        if not project_id:
            logger.warning("Study enrollment aborted: missing project_id.")
            raise StudyProjectNotFoundError

        if project_id not in settings.REGISTERED_STUDY_PROJECTS:
            logger.warning(
                "Study enrollment aborted: tried to access project that is not "
                "registered as a study project."
            )
            raise ProjectNotRegisteredAsStudyError

        try:
            return DonationProject.objects.get(url_id=project_id)
        except DonationProject.DoesNotExist as e:
            logger.warning(
                "Study enrollment aborted: project lookup failed (project_id=%r).",
                project_id,
            )
            raise StudyProjectNotFoundError from e

    @staticmethod
    def _reset_ddm_session(request: HttpRequest, project):
        """Reset any stale DDM participation session for this project so a
        fresh participant is created on the next donation step."""
        ddm_session_id = get_participation_session_id(project)
        request.session.pop(ddm_session_id, None)

    @staticmethod
    def _enroll_participant(
        request: HttpRequest,
        project: DonationProject,
        method: DonationMethod,
        url_params: dict,
    ):
        create_participation_session(request, project)
        participant = get_participant_from_session(request, project)
        participant.url_parameter = url_params
        participant.extra_data["method"] = method
        participant.extra_data[TRAIL_KEY] = (
            get_papi_trail()
            if method == DonationMethod.PORTABILITY.value
            else get_dlul_trail()
        )
        return participant


class StudyParticipationMixin:
    """Mixin for study participation views.

    Views inheriting this Mixin must set self.study_trail_step

    - Registers self.study_session in setup()
    - Adds get_project_from_study_session() method
    - Adds update_participant_trail() method
    """

    study_session: StudyParticipationSession
    study_session_project: DonationProject | None = None
    study_trail_step: DLULTrailSteps | PAPITrailSteps

    def setup(self, request, *args, **kwargs):
        """Reject requests without a fully enrolled study session.

        The check runs in ``setup()`` rather than ``dispatch()`` because
        ``DataDonationView.setup()`` (in DDM) calls ``_initialize_values``
        — and thus ``get_ddm_project`` — *before* ``dispatch`` is invoked.

        ``StudyParticipationSessionManager.get()`` returns ``None`` only
        when the session key is absent. ``StudyEnrollView`` calls
        ``reset()`` before validating ``project_id``, so a 404'd
        enrollment leaves a default-empty (but truthy) session behind.
        Gating additionally on ``ddm_project_id`` ensures only sessions
        that completed enrollment are accepted.
        """
        study_session = StudyParticipationSessionManager.from_request(request).get()
        if not study_session or not study_session.ddm_project_id:
            logger.error(
                "Study enrollment error: Registered attempt to access "
                "%s without registered study session.",
                self.__class__.__name__,
            )
            raise PermissionDenied
        self.study_session = study_session
        return super().setup(request, *args, **kwargs)

    def get_project_from_study_session(self) -> DonationProject:
        if self.study_session_project:
            return self.study_session_project
        try:
            project = DonationProject.objects.get(
                url_id=self.study_session.ddm_project_id
            )
        except DonationProject.DoesNotExist as e:
            raise StudyProjectNotFoundError from e

        self.study_session_project = project
        return project

    def update_participant_trail(
        self,
        request: HttpRequest,
        trail_step: DLULTrailSteps | PAPITrailSteps | None = None,
    ) -> None:
        project = self.get_project_from_study_session()
        participant = get_participant_from_session(request, project)
        if trail_step:
            update_participant_trail(participant, trail_step)
        else:
            update_participant_trail(participant, self.study_trail_step)

    def add_url_parameter_to_context(self, context: dict[str, Any]) -> None:
        """Adds "url_parameters" to context (excluding 'method' and 'project_id'."""
        url_parameters = self.study_session.url_parameters.copy()
        url_parameters.pop("method", None)
        url_parameters.pop("project_id", None)
        context["url_parameters"] = urlencode(url_parameters, doseq=True)


class DownloadUploadView(StudyParticipationMixin, BaseDonationViewDDM):
    """View to connect study participants to DDM without login.

    Participants must be redirected to this view via StudyEnrollView, otherwise
    the request will be rejected.
    """

    template_name = "studies/datadonation/download_upload.html"

    step_name = StudiesURLShortcut.DONATION_DDM
    steps = _STUDIES_FLOW_STEPS

    study_trail_step = DLULTrailSteps.INSTRUCTIONS

    def get_object(self, queryset: QuerySet | None = None) -> DonationProject:
        """Return the DDM project pinned on the study session at enrolment."""
        return self.get_project_from_study_session()

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        show_app_instruction = self.study_session.url_parameters.get(
            "appinstruction", "1"
        )

        reminder_registration_endpoint = reverse(
            "mdm:userflow:studies:dlul_register_got_reminder_info"
        )

        context.update(
            {
                "default_instruction": "app"
                if show_app_instruction == "1"
                else "browser",
                "seconds_until_reminder": SECONDS_TO_REMINDER,
                "reminder_registration_endpoint": reminder_registration_endpoint,
            }
        )
        return context

    def update_participant_information(self, request) -> None:
        """Add url parameters to participant information."""
        update_participant_trail(self.participant, self.study_trail_step)

    def initialize_statistics_request(self) -> StatisticsRequest:
        """Overwrite to create statistics request without user profile."""
        return StatisticsRequest.objects.create(participant=self.participant)

    def post_redirect_url(self) -> str:
        return reverse(StudiesURLShortcut.QUESTIONNAIRE)


# PORTABILITY VIEWS
class PortabilityEntryView(StudyParticipationMixin, port_views.TikTokAuthView):
    """View to connect study participants to portability API without login.

    Participants must be redirected to this view via StudyEnrollView, otherwise
    the request will be rejected.
    """

    template_name = "studies/portability/portability_entry.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["study_redirect_link"] = get_ddm_redirect_link(
            self.study_session, {"status": "aborted"}
        )
        return context


class PortabilityWaitingView(
    StudyParticipationMixin,
    AddUserflowSessionMixin,
    port_views.TikTokAwaitDataDownloadView,
):
    template_name = "studies/portability/tiktok_await_download.html"
    study_trail_step = PAPITrailSteps.WAITING_VIEW

    def validate_userflow_session(
        self, request, *args, **kwargs
    ) -> HttpResponseRedirect | None:
        """Bypassed in studies flow."""
        return None

    def get_context_data(self, **kwargs):
        self.update_participant_trail(self.request)

        context = super().get_context_data(**kwargs)
        context["project_id"] = self.study_session.ddm_project_id
        return context


def get_ddm_redirect_link(
    study_session: StudyParticipationSession,
    extra_param: dict[str, str] | None = None,
) -> str | None:
    """Constructs a redirect link based on the DDM project setting.

    If the DDM project has a redirect target enabled and configured, this
    target will be used as the redirect link. The string passed as extra_param
    will be appended to the redirect link.

    If the DDM project has no redirect target enabled or configured, or no linked
    DDM project can be identified, None will be returned.

    Args:
        study_session: A study participant session.
        extra_param: A dictionary containing url parameters to be attached to
            the end of the redirect link (e.g., {"status": "failed"}). If
            variable is present in the original redirect link, the original
            value will be replaced with the one provided here.

    Returns:
        The constructed redirect link if the DDM project has redirect enabled.
        None otherwise.
    """
    try:
        ddm_project = DonationProject.objects.get(url_id=study_session.ddm_project_id)
    except DonationProject.DoesNotExist:
        logger.exception(
            "get_ddm_redirect_link called without valid ddm project id in study session"
        )
        return None

    if not ddm_project.redirect_enabled:
        return None

    # Render redirect link
    template_context = {
        "project_id": ddm_project.url_id,
        "url_parameter": study_session.url_parameters,
    }

    redirect_link = render_user_content(ddm_project.redirect_target, template_context)

    if extra_param:
        parsed = urlparse(redirect_link)
        # parse_qs returns lists; flatten to single values for merging
        existing_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        existing_params.update(extra_param)  # extra_param values overwrite duplicates
        new_query = urlencode(existing_params)
        redirect_link = urlunparse(parsed._replace(query=new_query))

    return str(redirect_link)


class PortabilityAbortView(StudyParticipationMixin, TemplateView):
    """Displayed to participants who abort the portability flow.

    Participants can abort the flow by clicking on "cancel" on TikTok's authentication
    page. Template includes a redirect link as defined in the DDM project with a
    url parameter "status=aborted" attached to it.
    """

    template_name = "studies/portability/participation_aborted.html"
    study_trail_step = PAPITrailSteps.ABORT_VIEW

    def get_context_data(self, **kwargs):
        self.update_participant_trail(self.request)

        context = super().get_context_data(**kwargs)
        self.add_url_parameter_to_context(context)
        context["study_redirect_link"] = get_ddm_redirect_link(
            self.study_session, {"status": "aborted"}
        )
        context["project_id"] = self.study_session.ddm_project_id
        return context


class PortabilityErrorView(StudyParticipationMixin, TemplateView):
    """Displayed to participants who experienced an error in the portability flow.

    Template includes a redirect link as defined in the DDM project with a
    url parameter "status=failed" attached to it.
    """

    template_name = "studies/portability/participation_failed.html"
    study_trail_step = PAPITrailSteps.ERROR_VIEW

    def get_context_data(self, **kwargs):
        """Adds participant and project information to context.

        Necessary for correct redirect in the case of a connection failure.
        """
        self.update_participant_trail(self.request)

        context = super().get_context_data(**kwargs)
        self.add_url_parameter_to_context(context)
        context["study_redirect_link"] = get_ddm_redirect_link(
            self.study_session, {"status": "failed"}
        )
        context["project_id"] = self.study_session.ddm_project_id
        return context


AWAIT_PARTIALS_PATH = "studies/portability/await_partials/"


class CheckDownloadAvailabilityView(
    StudyParticipationMixin, port_views.TikTokCheckDownloadAvailabilityView
):
    """Returns appropriate status for the download availability.

    Returns rendered html partial and intended to be called by an HTMX component.
    """

    template_name = None  # Note: is assigned in get_context_data of parent

    template_pending = AWAIT_PARTIALS_PATH + "_data_download_pending_msg.html"
    template_success = AWAIT_PARTIALS_PATH + "_data_download_available_msg.html"
    template_error = AWAIT_PARTIALS_PATH + "_data_download_error_msg.html"
    template_expired = AWAIT_PARTIALS_PATH + "_data_download_expired_msg.html"

    def get_data_request(self):
        open_id = self.port_session.get_tiktok_open_id()
        return (
            TikTokDataRequest.objects.filter(
                open_id=open_id,
                download_succeeded=False,
            )
            .exclude(
                status__in=[
                    TikTokDataRequest.State.EXPIRED,
                    TikTokDataRequest.State.CANCELLED,
                ]
            )
            .first()
        )

    def get_context_data(self, **kwargs):
        """Adds participant and project information to context.

        Necessary for correct redirect in the case of a connection failure.
        """
        context = super().get_context_data(**kwargs)
        self.add_url_parameter_to_context(context)
        context["project_id"] = self.study_session.ddm_project_id

        # Determine whether reminder message should be displayed
        if self.template_name == self.template_pending:
            show_reminder_msg = False
            data_request = self.get_data_request()
            if data_request is None:
                # Can happen if a concurrent request (e.g. a second open tab)
                # changed the request's status between the parent view's
                # lookup and this one. Skip the reminder rather than 500.
                logger.warning(
                    "CheckDownloadAvailabilityView: no matching TikTokDataRequest "
                    "found while template_name was template_pending."
                )
            elif timezone.now() - data_request.issued_at > timedelta(
                seconds=SECONDS_TO_REMINDER
            ):
                show_reminder_msg = True

            if show_reminder_msg:
                self.update_participant_trail(
                    self.request, PAPITrailSteps.WAITING_REMINDER
                )

            context["show_reminder_msg"] = show_reminder_msg

        elif self.template_name == self.template_error:
            context["study_redirect_link"] = get_ddm_redirect_link(
                self.study_session, {"status": "failed"}
            )

            self.update_participant_trail(self.request, PAPITrailSteps.WAITING_ERROR)

        elif self.template_name == self.template_success:
            self.update_participant_trail(self.request, PAPITrailSteps.WAITING_SUCCESS)

        return context


# TODO: Implement better inheritance from mydigitalmeal.datadonation view.
class PortabilityReviewView(
    port_views.AuthenticationRequiredMixin,
    port_views.ActiveAccessTokenRequiredMixin,
    port_views.PortabilitySessionMixin,
    DownloadUploadView,
):
    template_name = "datadonation/portability/tiktok_review.html"
    study_trail_step = PAPITrailSteps.UPLOAD

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if settings.DEBUG:
            download_url = reverse("tiktok_download_mock_data")
        else:
            download_url = reverse("tiktok_download_data")

        context["tiktok_download_url"] = download_url
        context["fail_redirect_url"] = reverse("mdm:userflow:studies:port_tt_failed")
        context["portability_view"] = True
        return context

    def get_uploader_configs(self) -> list:
        """Overwritten to remove instructions from FileUploader."""
        project_uploaders = FileUploader.objects.filter(project=self.object)
        configs = UploaderConfigService.create_configs(
            project_uploaders, self.participant
        )
        # Remove Instructions
        for uploader in configs:
            uploader["instructions"] = []
        return configs

    def update_participant_information(self, request) -> None:
        """Add url parameters to participant information."""
        update_participant_trail(self.participant, self.study_trail_step)


class StudyQuestionnaireView(StudyParticipationMixin, QuestionnaireView):
    template_name = "mdm_questionnaire/questionnaire.html"
    step_name = StudiesURLShortcut.QUESTIONNAIRE
    steps = _STUDIES_FLOW_STEPS
    study_trail_step = PAPITrailSteps.QUESTIONNAIRE

    def get_object(self, queryset: QuerySet | None = None) -> DonationProject:
        """Return the DDM project pinned on the study session at enrolment."""
        return self.get_project_from_study_session()

    def get_context_data(self, **kwargs):
        self.update_participant_trail(self.request)

        context = super().get_context_data(**kwargs)
        context["project_slug"] = self.object.slug
        return context

    def current_step_url(self) -> str:
        return get_current_step_url(self.steps, self.current_step, self.object.slug)

    def next_step_url(self) -> str:
        return get_next_step_url(self.steps, self.current_step, self.object.slug)

    def post(self, request: HttpRequest, *args, **kwargs):
        """Overwrite to redirect to report view."""
        super().post(request, **kwargs)
        return HttpResponseRedirect(reverse(StudiesURLShortcut.DEBRIEFING))


class StudyDebriefingView(StudyParticipationMixin, DebriefingView):
    template_name = "studies/debriefing.html"
    step_name = StudiesURLShortcut.DEBRIEFING
    steps = _STUDIES_FLOW_STEPS
    study_trail_step = PAPITrailSteps.DEBRIEF

    def get_object(self, queryset: QuerySet | None = None) -> DonationProject:
        """Return the DDM project pinned on the study session at enrolment."""
        return self.get_project_from_study_session()

    def inactive_url(self) -> str:
        raise ProjectInactiveError

    def current_step_url(self) -> str:
        return get_current_step_url(self.steps, self.current_step, self.object.slug)

    def next_step_url(self) -> str:
        return get_next_step_url(self.steps, self.current_step, self.object.slug)

    def get(self, request: HttpRequest, *args, **kwargs):
        """Overwrite to include _mark_study_flow_completed and update
        participant trail."""
        context = self.get_context_data(object=self.object)
        self.extra_before_render(request)
        response = self.render_to_response(context)

        # Marking happens *after* render so a failed render doesn't leave
        # the participant in a half-completed state. Re-visits
        # to the debriefing page (refresh, back button) just re-mark.
        self._mark_study_flow_completed(request)
        self.update_participant_trail(request)
        return response

    @staticmethod
    def _mark_study_flow_completed(request) -> None:
        """Flag the study session as done so downstream routers
        (``PortabilityCallbackRouterView``, ``PortabilityAuthRetryRouterView``)
        send any subsequent OAuth-related traffic through the regular MDM
        path instead of back into the studies flow.
        """
        StudyParticipationSessionManager.from_request(request).update(
            completed=True,
        )


def register_got_reminder_info(request):
    """Quick and dirty helper method to register whether reminder info was displayed
    in the download-upload path.
    """
    if request.method != "POST":
        return JsonResponse({"status": "invalid method"}, status=405)

    study_session = StudyParticipationSessionManager.from_request(request).get()
    if not study_session:
        logger.warning("register_got_reminder_info: no study session found")
        return JsonResponse({"status": "no session"}, status=400)

    project = DonationProject.objects.filter(
        url_id=study_session.ddm_project_id
    ).first()
    if not project:
        logger.warning(
            "register_got_reminder_info: no project for url_id=%s",
            study_session.ddm_project_id,
        )
        return JsonResponse({"status": "no project"}, status=400)

    participant = get_participant_from_session(request, project)
    if not participant:
        logger.warning(
            "register_got_reminder_info: no participant for project=%s", project.url_id
        )
        return JsonResponse({"status": "no participant"}, status=400)

    logger.info(
        "register_got_reminder_info: recorded 'c_got_reminder_info' for "
        "participant=%s (project=%s)",
        participant.pk,
        project.url_id,
    )
    update_participant_trail(participant, "c_got_reminder_info")
    return JsonResponse({"status": "ok"})


_REPORT_MAX_AGE = timedelta(weeks=4)


def participant_can_access_report(participant: Participant) -> bool:
    """Tests whether participant can access report.

    Gates on:

    - That project is still ``active``.
    - The participation is at most ``_REPORT_MAX_AGE`` old, measured from
      ``Participant.start_time`` (i.e. when the participant enrolled).
    """
    if not participant.project.active:
        logger.info(
            "Study report blocked: project inactive (participant=%s).",
            participant.external_id,
        )
        return False
    if timezone.now() - participant.start_time > _REPORT_MAX_AGE:
        logger.info(
            "Study report blocked: participation older than "
            "REPORT_MAX_AGE (participant=%s).",
            participant.external_id,
        )
        return False
    return True


class StudyReportView(TemplateView):
    """Public report page for study participants.

    Authentication is by URL ``participant_id`` (no session), so the page
    is reload-safe and shareable. Access is gated on:

    - The participant exists and belongs to a project on the
      ``REGISTERED_STUDY_PROJECTS`` allowlist.
    - That project is still ``active``.
    - The participation is at most ``REPORT_MAX_AGE`` old, measured from
      ``Participant.start_time`` (i.e. when the participant enrolled).

    Any gate failure returns 404 (we deliberately do not leak which
    condition failed).

    Note: ``StudyStatisticsView`` serves the same underlying data via
    its HTMX polling endpoint and is *not* yet gated the same way — if
    you want to enforce the gates there too, push the same checks into
    its ``get_participant``.
    """

    template_name = "studies/report/base.html"

    def get(self, request, *args, **kwargs):
        participant_id = self.kwargs.get("participant_id")
        try:
            participant = Participant.objects.select_related("project").get(
                external_id=participant_id,
                project__url_id__in=settings.REGISTERED_STUDY_PROJECTS,
            )
        except Participant.DoesNotExist as e:
            logger.info(
                "Study report blocked: unknown participant id=%r.",
                participant_id,
            )
            raise Http404 from e

        if not participant_can_access_report(participant):
            raise Http404

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["participant_id"] = self.kwargs.get("participant_id")
        return context


class StudyStatisticsView(BaseStatisticsView):
    """Separate studies statistics view to retrieve statistics based on participant.

    Access is gated on:

    - The participant exists and belongs to a project on the
      ``REGISTERED_STUDY_PROJECTS`` allowlist.
    - That project is still ``active``.
    - The participation is at most ``REPORT_MAX_AGE`` old, measured from
      ``Participant.start_time`` (i.e. when the participant enrolled).
    """

    template_name = "studies/report/partials/_combined_statistics.html"
    session_invalid_redirect = "mdm:userflow:landing_page"
    report_unavailable_redirect = StudiesURLShortcut.REPORT_UNAVAILABLE

    def get_participant(self) -> Participant | None:
        return Participant.objects.get(
            external_id=self.kwargs.get("participant_id"),
            project__url_id__in=settings.REGISTERED_STUDY_PROJECTS,
        )

    def validate_userflow_session(self, request, *args, **kwargs):
        """Overwrites session validation of regular MDM flow."""
        return

    def get(self, request, *args, **kwargs):  # noqa: PLR0911
        """Overwrites parent method to retrieve statistics based on passed ID.

        A participant has two ``StatisticsRequest`` rows (interval + full,
        see ``BaseDonationViewDDM.initialize_statistic_computation``), but
        ``StatisticsRequest`` itself doesn't record which is which - that
        only becomes visible once a request finishes and creates its
        ``TikTokWatchHistoryStatistics`` child row (which carries
        ``scope``). Immediately after enrolment, in a real deployment
        (Celery not eager), neither request has a child row yet.

        The request is therefore resolved  defensively in stages:
        gather every request for the participant, try to resolve the specific
        interval-scoped one, and only treat the "not found" case as an error
        once every request has reached a terminal state (i.e. it's not just
        still computing).
        """
        try:
            participant = self.get_participant()
        except Participant.DoesNotExist:
            logger.warning("Study statistics view called without participant ID.")
            return self.htmx_redirect(StudiesURLShortcut.REPORT_UNAVAILABLE)

        if not participant or not participant_can_access_report(participant):
            return self.htmx_redirect(StudiesURLShortcut.REPORT_UNAVAILABLE)

        # `public_id` is deferred: a corrupted value in that column has
        # been observed to raise an unhandled ValueError the moment a row
        # is fetched, which would otherwise turn a single bad row into a 500 for
        # every poll of this HTMX endpoint. `pk` is used instead wherever
        # a request needs to be identified below.
        statistics_requests = list(
            StatisticsRequest.objects.defer("public_id").filter(participant=participant)
        )

        if not statistics_requests:
            logger.warning(
                "StatisticsRequest for participant %s not found",
                participant.external_id,
            )
            return self.htmx_redirect(self.session_invalid_redirect)

        self.statistics_request = next(
            (
                r
                for r in statistics_requests
                if r.get_statistics().filter(scope=StatisticsScope.INTERVAL).exists()
            ),
            None,
        )

        if self.statistics_request is None:
            if not all(r.is_ready() for r in statistics_requests):
                # At least one request (interval and/or full) is still
                # PENDING/RETRY (= "still computing" state, not an error).
                # Use one of the not-yet-ready requests so get_context_data()'s
                # own is_ready() check returns the loading state.
                self.statistics_request = next(
                    r for r in statistics_requests if not r.is_ready()
                )
                return self.render_statistics(**kwargs)

            # Every request has reached a terminal state and still no
            # INTERVAL result appeared - genuinely unavailable (failed, or
            # succeeded without ever producing interval-scope stats).
            logger.warning(
                "No INTERVAL-scope statistics found for participant %s "
                "after all statistics requests finished",
                participant.external_id,
            )
            return self.htmx_redirect(StudiesURLShortcut.REPORT_UNAVAILABLE)

        if self.statistics_request.has_failed():
            # Statistics computation failed
            logger.info(
                "Statistics request %s has failed and could not be "
                "retrieved (status details: %s)",
                self.statistics_request.pk,
                self.statistics_request.status_detail,
            )
            return self.htmx_redirect(StudiesURLShortcut.REPORT_UNAVAILABLE)

        # Pre-load stats here so we can redirect if needed
        if self.statistics_request.is_ready():
            self._stats = self.load_statistics()
            if self._stats is None:
                logger.info(
                    "Statistics request %s: Unable to load statistics "
                    "(status details: %s)",
                    self.statistics_request.pk,
                    self.statistics_request.status_detail,
                )
                return self.htmx_redirect(StudiesURLShortcut.REPORT_UNAVAILABLE)

        return self.render_statistics(**kwargs)
