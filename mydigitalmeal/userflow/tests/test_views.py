from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
from mydigitalmeal.profiles.models import MDMProfile
from mydigitalmeal.statistics.models import StatisticsRequest
from mydigitalmeal.userflow.constants import URLShortcut

User = get_user_model()


class TestLandingPageView(TestCase):
    def test_landing_page_is_accessible(self):
        response = self.client.get(reverse("userflow:landing_page"))

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
            "userflow:resume", kwargs={"request_id": str(self.stats_request.public_id)}
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

        _ = self.client.get(reverse("userflow:reset"))

        self.assertNotEqual(
            self.client.session[project_session_id].get("participant_id"),
            self.participant.id,
        )
        self.assertIsNone(self.client.session["mdm_session"].get("request_id"))
