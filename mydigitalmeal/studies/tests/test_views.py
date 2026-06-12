import importlib
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from ddm.participation.models import Participant
from ddm.participation.views import get_participation_session_id
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from mydigitalmeal.statistics.models import (
    StatisticsRequest,
    StatisticsScope,
    TikTokWatchHistoryStatistics,
)
from mydigitalmeal.studies import urls as studies_urls
from mydigitalmeal.studies.constants import STUDIES_SESSION_KEY, StudiesURLShortcut
from mydigitalmeal.studies.sessions import StudyParticipationSession
from mydigitalmeal.studies.views import (
    _REPORT_MAX_AGE,
    DownloadUploadView,
    StudyDebriefingView,
    StudyQuestionnaireView,
    participant_can_access_report,
)

User = get_user_model()


def _add_session_to_request(request):
    middleware = SessionMiddleware(get_response=lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


def _set_study_session_via_client(client, **fields):
    """Persist a StudyParticipationSession into the test client's session."""
    session = client.session
    session[STUDIES_SESSION_KEY] = StudyParticipationSession(**fields).to_dict()
    session.save()


def _make_owner_profile() -> ResearchProfile:
    owner = User.objects.create_user(
        email="projecttest@mail.com",
        username="projectuser",
        password="testpass",
    )
    return ResearchProfile.objects.create(user=owner)


@override_settings(REGISTERED_STUDY_PROJECTS=["enroll-test-project"])
class TestStudyEnrollView(TestCase):
    def setUp(self):
        self.url = reverse("mdm:userflow:studies:enroll")
        self.owner_profile = _make_owner_profile()
        # Pin ``url_id`` so the class-level ``REGISTERED_STUDY_PROJECTS``
        # override can name it explicitly. DDM auto-generates one otherwise.
        self.project_url_id = "enroll-test-project"
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
            url_id=self.project_url_id,
        )

    # ---- routing / status -------------------------------------------------

    def test_missing_project_id_returns_404(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_unknown_project_id_returns_404(self):
        response = self.client.get(self.url, {"project_id": "does-not-exist"})

        self.assertEqual(response.status_code, 404)

    def test_valid_project_id_papi_redirects_to_connect(self):
        response = self.client.get(
            self.url,
            {"project_id": self.project_url_id, "method": "port-api"},
        )

        self.assertRedirects(
            response,
            reverse("mdm:userflow:studies:port_tt_connect"),
            fetch_redirect_response=False,
        )

    def test_valid_project_id_dua_redirects_to_download_upload(self):
        response = self.client.get(
            self.url,
            {"project_id": self.project_url_id, "method": "download-upload"},
        )

        self.assertRedirects(
            response,
            reverse("mdm:userflow:studies:download_upload"),
            fetch_redirect_response=False,
        )

    def test_unknown_method_defaults_to_portability(self):
        response = self.client.get(
            self.url,
            {"project_id": self.project_url_id, "method": "banana"},
        )

        self.assertRedirects(
            response,
            reverse("mdm:userflow:studies:port_tt_connect"),
            fetch_redirect_response=False,
        )

    def test_missing_method_defaults_to_portability(self):
        response = self.client.get(self.url, {"project_id": self.project_url_id})

        self.assertRedirects(
            response,
            reverse("mdm:userflow:studies:port_tt_connect"),
            fetch_redirect_response=False,
        )

    # ---- session contents -------------------------------------------------

    def test_session_pinned_to_project_url_id(self):
        before = timezone.now()
        self.client.get(
            self.url,
            {"project_id": self.project_url_id, "method": "port-api"},
        )
        after = timezone.now()

        stored = self.client.session[STUDIES_SESSION_KEY]
        self.assertEqual(stored["ddm_project_id"], self.project_url_id)
        self.assertEqual(stored["method"], "port-api")
        enroll_time = datetime.fromisoformat(stored["enroll_time"])
        self.assertGreaterEqual(enroll_time, before)
        self.assertLessEqual(enroll_time, after)

    def test_session_url_parameters_filtered(self):
        self.client.get(
            self.url,
            {
                "project_id": self.project_url_id,
                "method": "port-api",
                "utm": "ok",
                "utm.source": "rejected_by_regex",
            },
        )

        stored = self.client.session[STUDIES_SESSION_KEY]
        # ``project_id`` / ``method`` are reserved; ``utm.source`` fails
        # the key regex; only ``utm`` survives.
        self.assertEqual(stored["url_parameters"], {"utm": "ok"})

    def test_subsequent_enrollment_resets_prior_session(self):
        # First enrollment populates url_parameters with ``utm``.
        self.client.get(
            self.url,
            {"project_id": self.project_url_id, "utm": "first"},
        )
        # Second enrollment has no ``utm`` and should fully replace the session.
        self.client.get(self.url, {"project_id": self.project_url_id})

        stored = self.client.session[STUDIES_SESSION_KEY]
        self.assertEqual(stored["url_parameters"], {})

    def test_clears_stale_ddm_participation_session(self):
        ddm_session_id = get_participation_session_id(self.project)
        session = self.client.session
        session[ddm_session_id] = {"foo": "bar"}
        session.save()

        self.client.get(self.url, {"project_id": self.project_url_id})

        self.assertNotIn(ddm_session_id, self.client.session)

    # ---- security regression markers --------------------------------------

    def test_404_does_not_leave_a_passing_session_behind(self):
        # 404'd enrollment leaves an empty (but truthy) session behind.
        self.client.get(self.url)

        self.assertIn(STUDIES_SESSION_KEY, self.client.session)
        self.assertIsNone(
            self.client.session[STUDIES_SESSION_KEY]["ddm_project_id"],
        )

        # Downstream view must still reject it.
        response = self.client.get(
            reverse("mdm:userflow:studies:download_upload"),
        )
        self.assertEqual(response.status_code, 403)


class TestRequireStudySessionMixin(TestCase):
    """Exercises ``RequireStudySessionMixin`` via ``DownloadUploadView``.

    The mixin is in ``DownloadUploadView``'s MRO, so hitting
    ``/study/dua/`` exercises it without needing a synthetic test view.
    """

    def setUp(self):
        self.url = reverse("mdm:userflow:studies:download_upload")
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
        )

    def test_rejects_when_no_session(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_rejects_when_session_has_no_ddm_project_id(self):
        _set_study_session_via_client(self.client)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_accepts_when_session_has_ddm_project_id(self):
        _set_study_session_via_client(
            self.client,
            ddm_project_id=str(self.project.url_id),
        )

        response = self.client.get(self.url)

        # Downstream may render 200 or take further branches; what matters
        # for the mixin is that the request is no longer rejected.
        self.assertNotEqual(response.status_code, 403)


class TestDownloadUploadView(TestCase):
    """Direct unit tests for the methods specific to ``DownloadUploadView``.

    Covers ``get_ddm_project`` and ``update_participant_information``. HTTP-level
    coverage of the mixin lives in `TestRequireStudySessionMixin`.
    """

    def setUp(self):
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
        )

    def _make_request_with_study_session(self, **session_fields):
        request = RequestFactory().get("/")
        request = _add_session_to_request(request)
        if session_fields:
            request.session[STUDIES_SESSION_KEY] = StudyParticipationSession(
                **session_fields
            ).to_dict()
            request.session.save()
        return request

    # ---- get_ddm_project ---------------------------------------------------

    def test_get_ddm_project_returns_pinned_project(self):
        request = self._make_request_with_study_session(
            ddm_project_id=str(self.project.url_id),
        )

        result = DownloadUploadView().get_ddm_project(request)

        self.assertEqual(result, self.project)

    def test_get_ddm_project_raises_when_pinned_project_deleted(self):
        request = self._make_request_with_study_session(
            ddm_project_id="ghost-project-id",
        )

        with self.assertRaises(DonationProject.DoesNotExist):
            DownloadUploadView().get_ddm_project(request)

    # ---- update_participant_information -----------------------------------

    def _make_view_for_participant(self, request) -> DownloadUploadView:
        view = DownloadUploadView()
        view.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
            extra_data={},
        )
        view.request = request
        return view

    def test_update_participant_information_writes_url_param(self):
        request = self._make_request_with_study_session(
            ddm_project_id=str(self.project.url_id),
            url_parameters={"utm": "ok"},
            enroll_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        view = self._make_view_for_participant(request)

        view.update_participant_information(request)

        view.participant.refresh_from_db()
        self.assertEqual(
            view.participant.extra_data["url_param"],
            {"utm": "ok"},
        )
        self.assertEqual(
            view.participant.extra_data["enroll_time"],
            "2024-01-01T12:00:00+00:00",
        )

    def test_update_participant_information_with_none_enroll_time(self):
        request = self._make_request_with_study_session(
            ddm_project_id=str(self.project.url_id),
            url_parameters={"utm": "ok"},
            # enroll_time deliberately omitted → defaults to None.
        )
        view = self._make_view_for_participant(request)

        view.update_participant_information(request)

        view.participant.refresh_from_db()
        self.assertIsNone(view.participant.extra_data["enroll_time"])


# ---- new views ------------------------------------------------------------


class TestStudyQuestionnaireView(TestCase):
    """Covers the studies-specific overrides on top of DDM's QuestionnaireView.

    Most of the heavy lifting (participant lookup, project resolution, current
    step) lives in DDM internals invoked by ``_initialize_values``. These
    tests patch ``_initialize_values`` so the overrides can be exercised
    without standing up a full DDM participation flow.
    """

    def setUp(self):
        self.url = reverse(StudiesURLShortcut.QUESTIONNAIRE)
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
        )

    def _make_init_at_step(self, step_index: int):
        """Return a closure suitable for patching ``_initialize_values``.

        ``patch.object(cls, "method", bound_method)`` does not re-bind the
        descriptor, so a bound TestCase helper would silently swallow the
        view instance. A free function captured by closure avoids that.
        """
        project = self.project

        def _init(view_self, _request):
            view_self.object = project
            view_self.participant = Participant.objects.create(
                project=project,
                start_time=timezone.now(),
                current_step=step_index,
            )
            view_self.current_step = step_index

        return _init

    def test_rejects_without_study_session(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_get_redirects_to_previous_step_when_step_mismatch(self):
        """If the participant's ``current_step`` is behind the questionnaire
        step, the view sends them to the earlier step (DL-UL in this case).
        """
        _set_study_session_via_client(
            self.client,
            ddm_project_id=str(self.project.url_id),
        )

        with patch.object(
            StudyQuestionnaireView,
            "_initialize_values",
            self._make_init_at_step(1),
        ):
            response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse(StudiesURLShortcut.DONATION_DDM),
            fetch_redirect_response=False,
        )

    def test_get_skips_to_debriefing_when_q_config_short(self):
        """DDM's heuristic: ``len(q_config) > 2`` means the project has any
        questions (``q_config`` is the JSON-encoded list; ``"[]"`` is len 2).
        The studies view fast-forwards to debriefing when there are none.
        """
        _set_study_session_via_client(
            self.client,
            ddm_project_id=str(self.project.url_id),
        )

        with (
            patch.object(
                StudyQuestionnaireView,
                "_initialize_values",
                self._make_init_at_step(2),
            ),
            patch.object(
                StudyQuestionnaireView,
                "get_context_data",
                return_value={"q_config": "[]"},
            ),
            patch.object(StudyQuestionnaireView, "set_step_completed"),
        ):
            response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse(StudiesURLShortcut.DEBRIEFING),
            fetch_redirect_response=False,
        )


class TestStudyDebriefingView(TestCase):
    """Covers the studies-specific overrides on top of DDM's DebriefingView."""

    def setUp(self):
        self.url = reverse(StudiesURLShortcut.DEBRIEFING)
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
        )

    def test_rejects_without_study_session(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_get_raises_404_when_project_inactive(self):
        self.project.active = False
        self.project.save()

        def init_inactive(view_self, _request):
            view_self.object = self.project
            view_self.participant = Participant.objects.create(
                project=self.project,
                start_time=timezone.now(),
                current_step=3,
            )
            view_self.current_step = 3

        view = StudyDebriefingView()
        # Drive ``_initialize_values`` manually so we can run the actual
        # ``get()`` without the rest of the DDM/HTTP plumbing.
        init_inactive(view, None)

        with self.assertRaises(Http404):
            view.get(RequestFactory().get(self.url))

    def test_get_renders_when_active_and_on_correct_step(self):
        _set_study_session_via_client(
            self.client,
            ddm_project_id=str(self.project.url_id),
        )

        def init_to_debriefing(view_self, _request):
            view_self.object = self.project
            view_self.participant = Participant.objects.create(
                project=self.project,
                start_time=timezone.now(),
                current_step=3,
            )
            view_self.current_step = 3

        # Avoid DDM's ``get_context_data``/``extra_before_render`` poking at
        # real questionnaire/donation state.
        with (
            patch.object(
                StudyDebriefingView,
                "_initialize_values",
                init_to_debriefing,
            ),
            patch.object(
                StudyDebriefingView,
                "get_context_data",
                return_value={},
            ),
            patch.object(
                StudyDebriefingView,
                "extra_before_render",
                return_value=None,
            ),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "studies/debriefing.html")


class TestParticipantCanAccessReportHelper(TestCase):
    def setUp(self):
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
            url_id="report-test-project",
        )
        self.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
            external_id="a" * 24,
        )

    def test_false_when_project_inactive(self):
        self.project.active = False
        self.project.save()

        result = participant_can_access_report(self.participant)

        self.assertFalse(result)

    def test_false_when_participation_older_than_max_age(self):
        # Push start_time just past the 4-week cap.
        self.participant.start_time = (
            timezone.now() - _REPORT_MAX_AGE - timedelta(seconds=1)
        )
        self.participant.save()

        result = participant_can_access_report(self.participant)

        self.assertFalse(result)

    def test_true_inside_the_max_age_window(self):
        # One minute inside the 4-week window → still allowed.
        self.participant.start_time = (
            timezone.now() - _REPORT_MAX_AGE + timedelta(minutes=1)
        )
        self.participant.save()

        result = participant_can_access_report(self.participant)

        self.assertTrue(result)


@override_settings(REGISTERED_STUDY_PROJECTS=["report-test-project"])
class TestStudyReportView(TestCase):
    """Public report shell. Authentication is by URL participant_id; access
    is additionally gated on (a) project still active and (b) participation
    no older than ``StudyReportView.REPORT_MAX_AGE``.
    """

    def setUp(self):
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
            url_id="report-test-project",
        )
        self.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
            external_id="a" * 24,
        )
        self.url = reverse(
            StudiesURLShortcut.REPORT,
            kwargs={"participant_id": self.participant.external_id},
        )

    def test_renders_for_active_recent_participation(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "studies/report/base.html")
        self.assertEqual(
            response.context["participant_id"],
            self.participant.external_id,
        )

    def test_no_session_required(self):
        """No ``RequireStudySessionMixin`` on this view by design. A fresh
        client (no session at all) can still load it as long as the
        access gates pass.
        """
        # Fresh test client → no session.
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_404_when_participant_unknown(self):
        url = reverse(
            StudiesURLShortcut.REPORT,
            kwargs={"participant_id": "z" * 24},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_404_when_participant_outside_registered_projects(self):
        with override_settings(REGISTERED_STUDY_PROJECTS=["different-project"]):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_404_when_project_inactive(self):
        self.project.active = False
        self.project.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_404_when_participation_older_than_max_age(self):
        # Push start_time just past the 4-week cap.
        self.participant.start_time = (
            timezone.now() - _REPORT_MAX_AGE - timedelta(seconds=1)
        )
        self.participant.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_renders_just_inside_the_max_age_window(self):
        # One minute inside the 4-week window → still allowed.
        self.participant.start_time = (
            timezone.now() - _REPORT_MAX_AGE + timedelta(minutes=1)
        )
        self.participant.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


@override_settings(REGISTERED_STUDY_PROJECTS=["study-project-url-id"])
class TestStudyStatisticsView(TestCase):
    """Polled HTMX endpoint that drives the report-loading UX.

    Authenticated only via the ``participant_id`` URL slug; ignores the
    userflow session (study participants have none).
    """

    def setUp(self):
        self.owner_profile = _make_owner_profile()
        self.project = DonationProject.objects.create(
            owner=self.owner_profile,
            slug="some-study",
            url_id="study-project-url-id",
        )
        self.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
            external_id="a" * 24,  # DDM requires exactly 24 chars
        )
        # ``tiktok_statistics`` is not (yet) on ``StudiesURLShortcut``; using
        # the string form. If it gets added later, swap in the enum value.
        self.url = reverse(
            "mdm:userflow:studies:tiktok_statistics",
            kwargs={"participant_id": self.participant.external_id},
        )

    def test_no_session_required(self):
        """``validate_userflow_session`` is overridden to a no-op so study
        participants (who have no userflow session) can reach this view.
        """
        # No StatisticsRequest yet → we expect the "no stats request"
        # HX-Redirect, not the "session invalid" redirect to OVERVIEW that
        # the parent class would emit.
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("HX-Redirect", response.headers)
        self.assertEqual(
            response.headers["HX-Redirect"],
            reverse("mdm:userflow:landing_page"),
        )

    def test_participant_outside_registered_projects_redirects(self):
        """A participant whose project is NOT in ``REGISTERED_STUDY_PROJECTS``
        should be treated as unknown → HX-Redirect to report_unavailable.
        """
        # Move the project out of the allowlist via override_settings on
        # this single call.
        with override_settings(REGISTERED_STUDY_PROJECTS=["different-project"]):
            response = self.client.get(self.url)

        self.assertEqual(
            response.headers["HX-Redirect"],
            reverse(StudiesURLShortcut.REPORT_UNAVAILABLE),
        )

    def test_unknown_participant_id_redirects_to_report_unavailable(self):
        """``Participant.DoesNotExist`` must be caught and converted to an
        HX-Redirect rather than 500.
        """
        url = reverse(
            "mdm:userflow:studies:tiktok_statistics",
            kwargs={"participant_id": "z" * 24},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.headers["HX-Redirect"],
            reverse(StudiesURLShortcut.REPORT_UNAVAILABLE),
        )

    def test_redirects_to_report_unavailable_when_stats_request_failed(self):
        """A FAILED statistics request → HX-Redirect to report_unavailable.

        Note: the view's filter joins on
        ``tiktok_wh_statistics__scope=INTERVAL``, so the test must also
        create a TikTokWatchHistoryStatistics row of that scope for the
        filter to find anything.
        """
        stats_request = StatisticsRequest.objects.create(
            participant=self.participant,
            status=StatisticsRequest.States.FAILED,
        )
        TikTokWatchHistoryStatistics.objects.create(
            request=stats_request,
            scope=StatisticsScope.INTERVAL,
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.headers["HX-Redirect"],
            reverse(StudiesURLShortcut.REPORT_UNAVAILABLE),
        )

    def test_renders_when_stats_request_pending(self):
        """A PENDING request should render the template with no HX-Redirect.

        This was the regression-marker that previously had to be skipped:
        the original ``super().get(...)`` at the end of
        ``StudyStatisticsView.get`` triggered ``BaseStatisticsView.get`` to
        re-fetch the statistics request from the userflow session, which
        always missed for study participants and emitted an HX-Redirect.
        The fix renders directly via ``get_context_data`` +
        ``render_to_response``.
        """
        stats_request = StatisticsRequest.objects.create(
            participant=self.participant,
            status=StatisticsRequest.States.PENDING,
        )
        TikTokWatchHistoryStatistics.objects.create(
            request=stats_request,
            scope=StatisticsScope.INTERVAL,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Redirect", response.headers)
        self.assertFalse(response.context["statistics_ready"])


# ---- smoke tests ----------------------------------------------------------


class TestStudiesModuleSmoke(TestCase):
    def test_views_module_imports(self):
        importlib.import_module("mydigitalmeal.studies.views")

    def test_all_urls_resolve(self):
        for pattern in studies_urls.urlpatterns:
            name = f"mdm:userflow:studies:{pattern.name}"

            if pattern.name in ["report", "tiktok_statistics"]:
                reverse(name, kwargs={"participant_id": "test213"})
            else:
                reverse(name)
