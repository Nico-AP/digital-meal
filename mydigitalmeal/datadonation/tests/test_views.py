import io
import json
import zipfile
from unittest.mock import MagicMock, patch

from ddm.datadonation.models import DonationBlueprint, FileUploader
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from mydigitalmeal.datadonation.constants import (
    TIKTOK_PROJECT_SLUG,
    TIKTOK_WATCH_HISTORY_BP_NAME,
)
from mydigitalmeal.datadonation.views.ddm import DonationViewDDM
from mydigitalmeal.profiles.models import MDMProfile
from mydigitalmeal.statistics.models import StatisticsRequest, StatisticsScope
from mydigitalmeal.userflow.sessions import UserflowSessionManager

User = get_user_model()


def add_session_to_request(request):
    """Helper function to add session to request"""
    middleware = SessionMiddleware(get_response=lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


class TestDonationViewDDM(TestCase):
    def setUp(self):
        class TestView(DonationViewDDM):
            pass

        self.view = TestView.as_view()

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
        uploader = FileUploader.objects.create(
            project=self.project,
        )
        self.blueprint = DonationBlueprint.objects.create(
            project=self.project,
            file_uploader=uploader,
            name=TIKTOK_WATCH_HISTORY_BP_NAME,
            expected_fields='"date", "link"',
        )

        self.user = User.objects.create_user(
            email="test@mail.com",
            username="testuser",
            password="testpass",
        )

        self.mdm_profile = MDMProfile.objects.create(user=self.user)

    def create_request(self, with_user: bool = True):  # noqa: FBT002
        request = RequestFactory().get("/")
        request = add_session_to_request(request)
        request.user = self.user if with_user else AnonymousUser()
        return request

    def test_accessible_to_authenticated_user(self):
        request = self.create_request()
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test_correct_template_used(self):
        self.client.login(email="test@mail.com", password="testpass")
        response = self.client.get(
            reverse("mdm:userflow:datadonation:datadonation_ddm")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datadonation/base_ddm.html")

    def test_not_accessible_to_unauthenticated_user(self):
        request = self.create_request(with_user=False)
        response = self.view(request)
        self.assertEqual(response.status_code, 302)

    def test_raises_404_when_project_does_not_exist(self):
        self.project.delete()
        request = self.create_request()

        with self.assertRaises(Http404):
            _ = self.view(request)

    def test_initialization_for_authenticated_user(self):
        request = self.create_request()
        participants_before = Participant.objects.count()

        response = self.view(request)

        participants_after = Participant.objects.count()
        new_participant = Participant.objects.latest("start_time")

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(participants_before, participants_after)
        self.assertEqual(new_participant.current_step, 1)

    def test_redirects_to_questionnaire(self):
        def get_zip_file(file_name, file_content):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                try:
                    zip_file.writestr(file_name, file_content.encode("utf-8"))
                except UnicodeEncodeError:
                    zip_file.writestr(
                        file_name, file_content.encode("utf-8", errors="replace")
                    )
            zip_buffer.seek(0)
            return zip_buffer

        extracted_data = [{"date": "2024-01-01", "link": "https://example.com"}]
        valid_data = {
            f"{self.blueprint.pk}": {
                "consent": True,
                "extractedData": extracted_data,
                "status": "complete",
            }
        }
        zip_buffer = get_zip_file("data_donation.json", json.dumps(valid_data))
        files = {"post_data": zip_buffer}

        self.client.login(email="test@mail.com", password="testpass")

        url = reverse("mdm:userflow:datadonation:datadonation_ddm")
        self.client.get(url)
        response = self.client.post(url, data=files)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("mdm:userflow:questionnaire:questionnaire"),
            target_status_code=302,  # Redirects to report if no questionnaire exists
        )


class TestDonationViewDDMStatisticsComputation(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@mail.com",
            username="testuser",
            password="testpass",
        )
        self.mdm_profile = MDMProfile.objects.create(user=self.user)

        owner_profile = ResearchProfile.objects.create(user=self.user)
        self.project = DonationProject.objects.create(
            owner=owner_profile,
            slug=TIKTOK_PROJECT_SLUG,
        )
        uploader = FileUploader.objects.create(
            project=self.project,
        )
        self.blueprint = DonationBlueprint.objects.create(
            project=self.project,
            file_uploader=uploader,
            name=TIKTOK_WATCH_HISTORY_BP_NAME,
            expected_fields='"date", "link"',
        )
        self.participant = Participant.objects.create(
            project=self.project,
            start_time=timezone.now(),
            current_step=1,
        )

        request = RequestFactory().get("/")
        request.user = self.user
        request = add_session_to_request(request)

        self.view = DonationViewDDM()
        self.view.object = self.project
        self.view.participant = self.participant
        self.view.request = request
        self.view.userflow_session = UserflowSessionManager.from_request(request)

    def test_initialize_statistics_request(self):
        statistics_request = self.view.initialize_statistics_request()

        self.assertEqual(StatisticsRequest.objects.count(), 1)
        self.assertEqual(statistics_request.profile, self.mdm_profile)
        self.assertEqual(statistics_request.participant, self.participant)

    def test_validate_received_data_valid(self):
        bp_data = {
            "consent": True,
            "status": "success",
            "extractedData": [{"date": "2024-01-01", "link": "https://example.com"}],
        }
        is_valid = self.view.validate_received_data(self.blueprint, bp_data)
        self.assertTrue(is_valid)

    def test_validate_received_data_invalid(self):
        bp_data = {
            "consent": False,
            "status": "success",
            "extractedData": [{"date": "2024-01-01", "link": "https://example.com"}],
        }

        is_valid = self.view.validate_received_data(self.blueprint, bp_data)
        self.assertFalse(is_valid)

    @patch("mydigitalmeal.datadonation.views.ddm.group")
    @patch.object(DonationBlueprint, "validate_donation")
    def test_successful_task_scheduling(self, mock_validate, mock_group):
        mock_validate.return_value = True

        mock_group_instance = MagicMock()
        mock_group.return_value = mock_group_instance

        self.view.initialize_statistic_computation()

        self.assertEqual(mock_group.call_count, 1)
        group_args = mock_group.call_args[0]
        self.assertEqual(len(group_args), 2)

        # Check both scopes are present
        signatures = list(group_args)
        scopes = [sig.kwargs["statistics_scope"] for sig in signatures]
        self.assertIn(StatisticsScope.FULL, scopes)
        self.assertIn(StatisticsScope.INTERVAL, scopes)
