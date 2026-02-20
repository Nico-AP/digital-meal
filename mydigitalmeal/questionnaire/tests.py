from unittest.mock import patch

from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mydigitalmeal.datadonation.constants import TIKTOK_PROJECT_SLUG
from mydigitalmeal.questionnaire.views import MDMQuestionnaireView

User = get_user_model()


def add_session_to_request(request):
    """Helper function to add session to request"""
    middleware = SessionMiddleware(get_response=lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


class TestMDMQuestionnaireView(TestCase):
    def setUp(self):
        class TestView(MDMQuestionnaireView):
            pass

        self.view = TestView.as_view()
        self.user_creds = {
            "email": "test@mail.com",
            "password": "testpass",
        }
        User.objects.create_user(
            email="test@mail.com",
            username="testuser",
            password="testpass",
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
            current_step=2,
        )

    def add_participant_to_session(self):
        s = self.client.session
        s.update(
            {
                f"project-{self.project.pk}": {"participant_id": self.participant.id},
            },
        )
        s.save()

    @patch("ddm.participation.views.create_questionnaire_config")
    def test_accessible_to_authenticated_user(self, mock_config_creation):
        mock_config_creation.return_value = ["dummy 1", "dummy 2", "dummy 3"]
        self.participant.current_step = 2
        self.participant.save()

        self.client.login(**self.user_creds)
        self.add_participant_to_session()

        response = self.client.get(reverse("userflow:questionnaire:questionnaire"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mdm_questionnaire/questionnaire.html")

    def test_authenticated_user_without_donation_is_redirected(self):
        self.participant.current_step = 1
        self.participant.save()

        self.client.login(**self.user_creds)
        self.add_participant_to_session()

        response = self.client.get(reverse("userflow:questionnaire:questionnaire"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("userflow:datadonation:datadonation_ddm"),
        )

    def test_not_accessible_to_unauthenticated_user(self):
        response = self.client.get(reverse("userflow:questionnaire:questionnaire"))

        self.assertEqual(response.status_code, 302)

    def test_raises_404_when_project_does_not_exist(self):
        self.project.delete()
        self.client.login(**self.user_creds)

        response = self.client.get(reverse("userflow:questionnaire:questionnaire"))

        self.assertEqual(response.status_code, 404)

    def test_redirect_to_reports_when_no_questions_defined(self):
        self.client.login(**self.user_creds)
        self.add_participant_to_session()
        self.participant.current_step = 2
        self.participant.save()

        response = self.client.get(reverse("userflow:questionnaire:questionnaire"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("userflow:reports:tiktok_report"))
