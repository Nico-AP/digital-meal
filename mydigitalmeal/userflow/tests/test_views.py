from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
from mydigitalmeal.profiles.models import MDMProfile
from mydigitalmeal.statistics.models import StatisticsRequest
from mydigitalmeal.studies.sessions import (
    StudyParticipationSession,
    StudyParticipationSessionManager,
)
from mydigitalmeal.userflow.constants import URLShortcut

User = get_user_model()


class TestLandingPageView(TestCase):
    def test_landing_page_is_accessible(self):
        response = self.client.get(reverse("mdm:userflow:landing_page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "userflow/landing_page.html")


class TestOverviewView(TestCase):
    def setUp(self):
        self.url = reverse_lazy(URLShortcut.OVERVIEW)
        self.user = User.objects.create_user(
            email="test@mail.com",
            username="testuser",
            password="testpass",
        )
        self.profile = MDMProfile.objects.create(
            user=self.user,
        )

        project_owner = User.objects.create_user(
            email="projecttest@mail.com",
            username="projectuser",
            password="testpass",
        )
        owner_profile = ResearchProfile.objects.create(user=project_owner)
        self.project = DonationProject.objects.create(
            owner=owner_profile,
            slug=TIKTOK_PROJECT_SLUG,
        )

    def test_overview_page_is_accessible(self):
        StatisticsRequest.objects.create(profile=self.profile)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "userflow/overview.html")

    # TODO: Enable again when tested.
    # def test_overview_page_redirects_when_no_statistics_requests(self):
    #     self.client.force_login(self.user)  # noqa: ERA001
    #     response = self.client.get(self.url)  # noqa: ERA001
    #
    #     self.assertEqual(response.status_code, 302)  # noqa: ERA001
    #     self.assertRedirects(response, reverse(URLShortcut.DONATION_DDM))  # noqa: ERA001, E501

    def test_not_accessible_to_unauthenticated_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)


class TestUserflowResumeView(TestCase):
    def setUp(self):
        self.url = reverse_lazy(URLShortcut.OVERVIEW)
        self.user = User.objects.create_user(
            email="test@mail.com",
            username="testuser",
            password="testpass",
        )
        self.profile = MDMProfile.objects.create(
            user=self.user,
        )

        project_owner = User.objects.create_user(
            email="projecttest@mail.com",
            username="projectuser",
            password="testpass",
        )
        owner_profile = ResearchProfile.objects.create(user=project_owner)
        self.project = DonationProject.objects.create(
            owner=owner_profile,
            slug=TIKTOK_PROJECT_SLUG,
        )

        self.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
        )

        self.stats_request = StatisticsRequest.objects.create(
            profile=self.profile,
            participant=self.participant,
        )

    def test_correctly_updates_session(self):
        url = reverse(
            "mdm:userflow:resume",
            kwargs={"request_id": str(self.stats_request.public_id)},
        )

        self.client.force_login(self.user)
        _ = self.client.get(url)

        project_session_id = f"project-{self.project.pk}"
        self.assertEqual(
            self.client.session[project_session_id].get("participant_id"),
            self.participant.id,
        )
        self.assertEqual(
            self.client.session["mdm_session"].get("request_id"),
            str(self.stats_request.public_id),
        )


class TestUserflowResetView(TestCase):
    def setUp(self):
        self.url = reverse_lazy(URLShortcut.OVERVIEW)
        self.user = User.objects.create_user(
            email="test@mail.com",
            username="testuser",
            password="testpass",
        )
        self.profile = MDMProfile.objects.create(
            user=self.user,
        )

        project_owner = User.objects.create_user(
            email="projecttest@mail.com",
            username="projectuser",
            password="testpass",
        )
        owner_profile = ResearchProfile.objects.create(user=project_owner)
        self.project = DonationProject.objects.create(
            owner=owner_profile,
            slug=TIKTOK_PROJECT_SLUG,
        )

        self.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
        )

        self.stats_request = StatisticsRequest.objects.create(
            profile=self.profile,
            participant=self.participant,
        )

    def test_correctly_resets_session(self):
        self.client.force_login(self.user)
        project_session_id = f"project-{self.project.pk}"
        self.client.session[project_session_id] = {
            "participant_id": self.participant.id
        }
        self.client.session["mdm_session"] = {
            "statistics_requested": True,
            "request_id": str(self.stats_request),
        }
        self.client.session.modified = True

        _ = self.client.get(reverse("mdm:userflow:reset"))

        self.assertNotEqual(
            self.client.session[project_session_id].get("participant_id"),
            self.participant.id,
        )
        self.assertIsNone(self.client.session["mdm_session"].get("request_id"))


class TestPortabilityCallbackRouterView(TestCase):
    """Tests the post-OAuth routing between studies and datadonation flows."""

    def setUp(self):
        self.url = reverse_lazy("mdm:userflow:portability_callback_router")
        self.studies_target = reverse(
            "mdm:userflow:studies:port_tt_await_data",
        )
        self.datadonation_target = reverse(
            "mdm:userflow:datadonation:port_tt_await_data",
        )

    def _set_study_session(self, **fields) -> None:
        """Persist a StudyParticipationSession into the test client's session."""
        session = self.client.session
        session[StudyParticipationSessionManager.SESSION_KEY] = (
            StudyParticipationSession(**fields).to_dict()
        )
        session.save()

    def test_redirects_to_datadonation_when_no_study_session(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.datadonation_target,
            fetch_redirect_response=False,
        )

    def test_redirects_to_datadonation_when_study_session_has_no_project(self):
        # Mirrors the post-`reset()` state: dataclass exists with default-empty
        # fields. An empty dataclass is truthy, so the router must additionally
        # check `ddm_project_id` to avoid misrouting regular participants.
        self._set_study_session()

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.datadonation_target,
            fetch_redirect_response=False,
        )

    def test_redirects_to_studies_when_study_session_pinned_to_project(self):
        self._set_study_session(ddm_project_id="some-project")

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.studies_target,
            fetch_redirect_response=False,
        )

    def test_does_not_require_authentication(self):
        # Both downstream views enforce their own auth gates; the router
        # itself must remain unauthenticated so study participants (who never
        # log in) can pass through.
        self._set_study_session(ddm_project_id="some-project")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_falls_through_to_datadonation_when_study_completed(self):
        """Once ``study_session.completed`` is True (set by
        ``StudyDebriefingView`` after end-of-flow), any subsequent
        OAuth-callback traffic should route through the regular MDM
        flow rather than back into the studies flow.
        """
        self._set_study_session(
            ddm_project_id="some-project",
            completed=True,
        )

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.datadonation_target,
            fetch_redirect_response=False,
        )


class TestPortabilityAuthRetryRouterView(TestCase):
    """Routes the ``redirect_to_auth_view`` fallback to the right entry view.

    Shape mirrors ``TestPortabilityCallbackRouterView`` — same study-session
    branch logic, different downstream targets (the portability connect /
    entry views rather than the await views).
    """

    def setUp(self):
        self.url = reverse_lazy("mdm:userflow:portability_auth_router")
        self.studies_target = reverse("mdm:userflow:studies:port_tt_connect")
        self.datadonation_target = reverse(
            "mdm:userflow:datadonation:port_tt_connect",
        )

    def _set_study_session(self, **fields) -> None:
        session = self.client.session
        session[StudyParticipationSessionManager.SESSION_KEY] = (
            StudyParticipationSession(**fields).to_dict()
        )
        session.save()

    def test_redirects_to_datadonation_when_no_study_session(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.datadonation_target,
            fetch_redirect_response=False,
        )

    def test_redirects_to_studies_when_study_session_pinned_to_project(self):
        self._set_study_session(ddm_project_id="some-project")

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.studies_target,
            fetch_redirect_response=False,
        )

    def test_falls_through_to_datadonation_when_study_completed(self):
        """Same end-of-flow behaviour as the callback router: a
        ``completed`` study session means the participant should be
        treated as outside the studies flow.
        """
        self._set_study_session(
            ddm_project_id="some-project",
            completed=True,
        )

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            self.datadonation_target,
            fetch_redirect_response=False,
        )
