import json
from datetime import datetime, timedelta

from ddm.datadonation.models import DataDonation, DonationBlueprint, FileUploader
from ddm.datadonation.schemas import JSONParserConfig
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import digital_meal.reports.utils.tiktok.data as tiktok_data_utils
import digital_meal.reports.utils.tiktok.example_data as tiktok_data
import digital_meal.reports.utils.youtube.data as youtube_data_utils
import digital_meal.reports.utils.youtube.example_data as youtube_data
import digital_meal.reports.views.tiktok as tiktok_views
from digital_meal.tool.models import BaseModule, Classroom

User = get_user_model()


class TestReportsGeneralFunctionality(TestCase):
    """Tests for general report functionality.

    Tests:
    - Classroom expiration and related behavior
    - Class report accessibility for (non-)users
    - Class report rendering depending on number of participants.
    """

    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            "username": "username",
            "password": "123",
            "email": "username@mail.com",
        }
        cls.user = User.objects.create_user(**cls.base_creds)
        cls.research_profile = ResearchProfile.objects.create(user=cls.user)

        # Initialize a data donation project
        cls.project = DonationProject.objects.create(
            name="projectname",
            active=True,
            owner=cls.research_profile,
            contact_information="something",
            data_protection_statement="something",
            slug="slug",
        )

        cls.uploader = FileUploader.objects.create(
            project=cls.project,
            name="uploader",
            index=1,
            upload_type="zip file",
            combined_consent=True,
        )

        cls.blueprint = DonationBlueprint.objects.create(
            project=cls.project,
            name="Angesehene Videos",
            exp_file_format="json",
            file_uploader=cls.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        # Crate a module
        cls.module = BaseModule.objects.create(
            name="module-name",
            active=True,
            ddm_path="https://127.0.0.1:8000/",
            ddm_project_id=cls.project.url_id,
            report_prefix="youtube_",
        )

        # Create Classroom - not expired
        cls.classroom_regular = Classroom.objects.create(
            owner=cls.user,
            name="regular class",
            base_module=cls.module,
            school_level="primary",
            school_year=10,
            subject="languages",
            instruction_format="regular",
        )

        # Create expired classroom
        cls.classroom_expired = Classroom.objects.create(
            owner=cls.user,
            name="regular class",
            expiry_date=timezone.now(),
            base_module=cls.module,
            school_level="primary",
            school_year=10,
            subject="languages",
            instruction_format="regular",
        )

        cls.urls = {
            "main": reverse("tool_main_page"),
            "class_create": reverse("class_create"),
            "class_detail": reverse(
                "class_detail", kwargs={"url_id": cls.classroom_regular.url_id}
            ),
            "profile": reverse("profile"),
        }

    def setUp(self):
        self.client.login(**self.base_creds)
        self.htmx_headers = {"HTTP_HX-Request": "true"}

    def test_expired_classroom_does_not_show_report(self):
        report_url = reverse(
            "youtube_class_report", kwargs={"url_id": self.classroom_expired.url_id}
        )
        expired_url = reverse(
            "class_expired", kwargs={"url_id": self.classroom_expired.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expired_url)

    def test_class_report_is_accessible_by_owner(self):
        report_url = reverse(
            "youtube_class_report", kwargs={"url_id": self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)

    def test_class_report_is_not_accessible_when_logged_out(self):
        self.client.logout()
        login_url = reverse("account_login")
        report_url = reverse(
            "youtube_class_report", kwargs={"url_id": self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, login_url + f"?next={report_url}")

    def test_class_report_is_not_accessible_to_non_owner(self):
        self.client.logout()
        test_creds = {
            "username": "test_user",
            "password": "123",
            "email": "testuser@mail.com",
        }
        User.objects.create_user(**test_creds)
        self.client.login(**test_creds)
        report_url = reverse(
            "youtube_class_report", kwargs={"url_id": self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 403)

    def test_report_with_less_than_five_donations_does_not_show_report(self):
        report_url = reverse(
            "youtube_class_report_wh_sections",
            kwargs={"url_id": self.classroom_regular.url_id},
        )
        response = self.client.get(report_url, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reports/components/report_section_unavailable_class.html"
        )


class TestYouTubeReports(TestCase):
    """Tests YouTube reports.

    Tests if class, individual, and example reports are rendered correctly.
    """

    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            "username": "username",
            "password": "123",
            "email": "username@mail.com",
        }
        cls.user = User.objects.create_user(**cls.base_creds)
        cls.research_profile = ResearchProfile.objects.create(user=cls.user)

        # Initialize a data donation project
        cls.project = DonationProject.objects.create(
            name="youtube-test-project",
            active=True,
            owner=cls.research_profile,
            contact_information="something",
            data_protection_statement="something",
            slug="slug",
        )

        cls.uploader = FileUploader.objects.create(
            project=cls.project,
            name="youtube uploader",
            index=1,
            upload_type="zip file",
            combined_consent=True,
        )

        cls.watched_videos_bp = DonationBlueprint.objects.create(
            project=cls.project,
            name="Angesehene Videos",
            exp_file_format="json",
            file_uploader=cls.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        cls.searches_bp = DonationBlueprint.objects.create(
            project=cls.project,
            name="Suchverlauf",
            exp_file_format="json",
            file_uploader=cls.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        cls.subscriptions_bp = DonationBlueprint.objects.create(
            project=cls.project,
            name="Abonnierte Kanäle",
            exp_file_format="json",
            file_uploader=cls.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        # Crate a module
        cls.module = BaseModule.objects.create(
            name="module-name",
            active=True,
            ddm_path="https://127.0.0.1:8000/",
            ddm_project_id=cls.project.url_id,
            report_prefix="youtube_",
        )

        # Create Classroom - not expired
        cls.classroom = Classroom.objects.create(
            owner=cls.user,
            name="regular class",
            base_module=cls.module,
            school_level="primary",
            school_year=10,
            subject="languages",
            instruction_format="regular",
        )

        # Generate example data
        cls.watch_history_data = youtube_data.generate_synthetic_watch_history(
            datetime.now(), 10
        )
        cls.search_data = youtube_data.generate_synthetic_search_history(
            datetime.now(), 10
        )
        cls.subscription_data = [
            {"Channel ID|Kanal-ID|ID des cha.*|ID canale": "UC1yNl2E10ZzKApQdRuTQ6tw"},
            {"Channel ID|Kanal-ID|ID des cha.*|ID canale": "CC1yNl2E10ZzKApQdRuTQ6tw"},
        ]

        cls.htmx_headers = {"HTTP_HX-Request": "true"}

    def test_individual_report(self):
        # Create donation
        participant = Participant.objects.create(
            project=self.project,
            extra_data={},
            url_parameter={"class": self.classroom.url_id},
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=self.watched_videos_bp,
            consent=True,
            data=self.watch_history_data["data"],
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=self.searches_bp,
            consent=True,
            data=self.search_data["data"],
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=self.subscriptions_bp,
            consent=True,
            data=self.subscription_data,
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )

        # Watch history section
        report_url_wh = reverse(
            "youtube_individual_report_wh_sections",
            kwargs={
                "url_id": self.classroom.url_id,
                "participant_id": participant.external_id,
            },
        )
        response = self.client.get(report_url_wh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_watch_history_report_individual.html",
            "reports/components/watch_history_stats_section.html",
            "reports/components/watch_history_timeseries_section.html",
            "reports/components/watch_history_daily_heatmap_section.html",
            "reports/components/watch_history_fav_video_section.html",
            "reports/components/watch_history_fav_channels_section_individual.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

        # Search history section
        report_url_sh = reverse(
            "youtube_individual_report_sh_sections",
            kwargs={
                "url_id": self.classroom.url_id,
                "participant_id": participant.external_id,
            },
        )
        response = self.client.get(report_url_sh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_search_history_report_individual.html",
            "reports/components/search_history_wordcloud.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

    def test_classroom_report(self):
        # Create 5 donations
        for _ in range(5):
            participant = Participant.objects.create(
                project=self.project,
                extra_data={},
                url_parameter={"class": self.classroom.url_id},
                start_time=timezone.now(),
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.watched_videos_bp,
                consent=True,
                data=self.watch_history_data["data"],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.searches_bp,
                consent=True,
                data=self.search_data["data"],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.subscriptions_bp,
                consent=True,
                data=self.subscription_data,
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )

        self.client.login(**self.base_creds)

        # Watch history section
        report_url_wh = reverse(
            "youtube_class_report_wh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_url_wh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_watch_history_report_class.html",
            "reports/components/watch_history_stats_section.html",
            "reports/components/watch_history_timeseries_section.html",
            "reports/components/watch_history_daily_heatmap_section.html",
            "reports/components/watch_history_fav_video_section.html",
            "reports/components/watch_history_fav_channels_section_class.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

        # Search history section
        report_url_sh = reverse(
            "youtube_class_report_sh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_url_sh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_search_history_report_class.html",
            "reports/components/search_history_wordcloud.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

        # Subscription section
        report_url_subs = reverse(
            "youtube_class_report_sub_sections",
            kwargs={"url_id": self.classroom.url_id},
        )
        response = self.client.get(report_url_subs, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_subscriptions_report_class.html",
            "reports/components/subscribed_channels_section.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

    def test_classroom_report_with_mixed_timezone_watch_history(self):
        now = timezone.now()
        naive_entry = {
            "title": "Watched a video",
            "titleUrl": "https://www.youtube.com/watch?v=naive12345",
            "time": (now - timedelta(days=2)).replace(tzinfo=None).isoformat(),
        }
        aware_entry = {
            "title": "Watched another video",
            "titleUrl": "https://www.youtube.com/watch?v=aware67890",
            "time": (now - timedelta(days=1)).isoformat(),
        }

        for i in range(5):
            participant = Participant.objects.create(
                project=self.project,
                extra_data={},
                url_parameter={"class": self.classroom.url_id},
                start_time=timezone.now(),
            )
            entry = naive_entry if i % 2 == 0 else aware_entry
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.watched_videos_bp,
                consent=True,
                data=[entry],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )

        self.client.login(**self.base_creds)

        report_url_wh = reverse(
            "youtube_class_report_wh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_url_wh, **self.htmx_headers)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reports/components/watch_history_stats_section.html"
        )

    def test_youtube_example_report_wh_sections(self):
        url = reverse("youtube_example_report_wh_sections")
        response = self.client.get(url, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_watch_history_report_individual.html",
            "reports/components/watch_history_stats_section.html",
            "reports/components/watch_history_timeseries_section.html",
            "reports/components/watch_history_daily_heatmap_section.html",
            "reports/components/watch_history_fav_video_section.html",
            "reports/components/watch_history_fav_channels_section_individual.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

    def test_youtube_example_report_sh_sections(self):
        url = reverse("youtube_example_report_sh_sections")
        response = self.client.get(url, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/youtube/_search_history_report_individual.html",
            "reports/components/search_history_wordcloud.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)


class TestYouTubeVideoTitleExtraction(TestCase):
    def test_get_video_title_dict_skips_entries_without_title(self):
        watch_history = [
            {"titleUrl": "https://www.youtube.com/watch?v=has_title", "title": "A"},
            {"titleUrl": "https://www.youtube.com/watch?v=no_title"},
        ]
        titles = youtube_data_utils.get_video_title_dict(watch_history)
        self.assertEqual(titles, {"has_title": "A"})

    def test_clean_video_title_handles_missing_title(self):
        self.assertIsNone(youtube_data_utils.clean_video_title(None))
        self.assertEqual(
            youtube_data_utils.clean_video_title("Some Title"), "Some Title"
        )


class TestTikTokReports(TestCase):
    """Tests TikTok reports.

    Tests if class, individual, and example reports are rendered correctly.
    """

    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            "username": "username",
            "password": "123",
            "email": "username@mail.com",
        }
        cls.user = User.objects.create_user(**cls.base_creds)
        cls.research_profile = ResearchProfile.objects.create(user=cls.user)

        # Initialize a data donation project
        cls.project = DonationProject.objects.create(
            name="tiktok-test-project",
            active=True,
            owner=cls.research_profile,
            contact_information="something",
            data_protection_statement="something",
            slug="slug",
        )

        cls.uploader = FileUploader.objects.create(
            project=cls.project,
            name="tiktok uploader",
            index=1,
            upload_type="zip file",
            combined_consent=True,
        )

        cls.watched_videos_bp = DonationBlueprint.objects.create(
            project=cls.project,
            name="Angesehene Videos",
            exp_file_format="json",
            file_uploader=cls.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        cls.searches_bp = DonationBlueprint.objects.create(
            project=cls.project,
            name="Durchgeführte Suchen",
            exp_file_format="json",
            file_uploader=cls.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        # Crate a module
        cls.module = BaseModule.objects.create(
            name="module-name",
            active=True,
            ddm_path="https://127.0.0.1:8000/",
            ddm_project_id=cls.project.url_id,
            report_prefix="tiktok_",
        )

        # Create Classroom - not expired
        cls.classroom = Classroom.objects.create(
            owner=cls.user,
            name="regular class",
            base_module=cls.module,
            school_level="primary",
            school_year=10,
            subject="languages",
            instruction_format="regular",
        )

        # Generate example data
        cls.watch_history_data = tiktok_data.generate_synthetic_watch_history(
            datetime.now(), 10
        )
        cls.search_data = tiktok_data.generate_synthetic_search_history(
            datetime.now(), 10
        )

        cls.htmx_headers = {"HTTP_HX-Request": "true"}

    def test_individual_report(self):
        # Create donation
        participant = Participant.objects.create(
            project=self.project,
            extra_data={},
            url_parameter={"class": self.classroom.url_id},
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=self.watched_videos_bp,
            consent=True,
            data=self.watch_history_data["data"],
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=self.searches_bp,
            consent=True,
            data=self.search_data["data"],
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )
        report_url_wh = reverse(
            "tiktok_individual_report_wh_sections",
            kwargs={
                "url_id": self.classroom.url_id,
                "participant_id": participant.external_id,
            },
        )
        response = self.client.get(report_url_wh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/tiktok/_watch_history_report_individual.html",
            "reports/components/watch_history_stats_section.html",
            "reports/components/watch_history_timeseries_section.html",
            "reports/components/watch_history_daily_heatmap_section.html",
            "reports/components/watch_history_fav_video_section.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

        report_url_sh = reverse(
            "tiktok_individual_report_sh_sections",
            kwargs={
                "url_id": self.classroom.url_id,
                "participant_id": participant.external_id,
            },
        )
        response = self.client.get(report_url_sh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/tiktok/_search_history_report_individual.html",
            "reports/components/search_history_wordcloud.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

    def test_individual_report_alternate_blueprint_name(self):
        """Data donated under an alternate blueprint name (e.g. because the
        DDP export used a different file name than the primary
        "Angesehene Videos" / "Durchgeführte Suchen" blueprints) should
        still be picked up by the get_wh_data/get_search_data fallback.
        """
        alt_watched_videos_bp = DonationBlueprint.objects.create(
            project=self.project,
            name="watched_videos",
            exp_file_format="json",
            file_uploader=self.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )
        alt_searches_bp = DonationBlueprint.objects.create(
            project=self.project,
            name="searches",
            exp_file_format="json",
            file_uploader=self.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        participant = Participant.objects.create(
            project=self.project,
            extra_data={},
            url_parameter={"class": self.classroom.url_id},
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=alt_watched_videos_bp,
            consent=True,
            data=self.watch_history_data["data"],
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=alt_searches_bp,
            consent=True,
            data=self.search_data["data"],
            data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
        )

        report_url_wh = reverse(
            "tiktok_individual_report_wh_sections",
            kwargs={
                "url_id": self.classroom.url_id,
                "participant_id": participant.external_id,
            },
        )
        response = self.client.get(report_url_wh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reports/components/watch_history_stats_section.html"
        )

        report_url_sh = reverse(
            "tiktok_individual_report_sh_sections",
            kwargs={
                "url_id": self.classroom.url_id,
                "participant_id": participant.external_id,
            },
        )
        response = self.client.get(report_url_sh, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reports/components/search_history_wordcloud.html"
        )

    def test_classroom_report(self):
        # Create 5 donations
        for _ in range(5):
            participant = Participant.objects.create(
                project=self.project,
                extra_data={},
                url_parameter={"class": self.classroom.url_id},
                start_time=timezone.now(),
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.watched_videos_bp,
                consent=True,
                data=self.watch_history_data["data"],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.searches_bp,
                consent=True,
                data=self.search_data["data"],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )

        self.client.login(**self.base_creds)

        report_wh_url = reverse(
            "tiktok_class_report_wh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_wh_url, **self.htmx_headers)

        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/tiktok/_watch_history_report_class.html",
            "reports/components/watch_history_stats_section.html",
            "reports/components/watch_history_timeseries_section.html",
            "reports/components/watch_history_daily_heatmap_section.html",
            "reports/components/watch_history_fav_video_section.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

        report_sh_url = reverse(
            "tiktok_class_report_sh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_sh_url, **self.htmx_headers)

        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/tiktok/_search_history_report_class.html",
            "reports/components/search_history_wordcloud.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

    def test_classroom_report_with_mixed_timezone_watch_history(self):
        now = timezone.now()
        naive_entry = {
            "(D|d)ate": (now - timedelta(days=2)).replace(tzinfo=None).isoformat(),
            "(L|l)ink": "https://www.tiktok.com/@/video/naive/",
        }
        aware_entry = {
            "(D|d)ate": (now - timedelta(days=1)).isoformat(),
            "(L|l)ink": "https://www.tiktok.com/@/video/aware/",
        }

        for i in range(5):
            participant = Participant.objects.create(
                project=self.project,
                extra_data={},
                url_parameter={"class": self.classroom.url_id},
                start_time=timezone.now(),
            )
            entry = naive_entry if i % 2 == 0 else aware_entry
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.watched_videos_bp,
                consent=True,
                data=[entry],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )

        self.client.login(**self.base_creds)

        report_wh_url = reverse(
            "tiktok_class_report_wh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_wh_url, **self.htmx_headers)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reports/components/watch_history_stats_section.html"
        )

    def test_classroom_report_with_participation_split_across_blueprint_names(self):
        """Regression test: the five-participant privacy minimum for class
        reports must be evaluated across all blueprint name variants for a
        data type together, not per individual blueprint name.
        overall."""
        alt_watched_videos_bp = DonationBlueprint.objects.create(
            project=self.project,
            name="watched_videos",
            exp_file_format="json",
            file_uploader=self.uploader,
            parser_config=JSONParserConfig().model_dump(),
        )

        blueprints = [self.watched_videos_bp] * 3 + [alt_watched_videos_bp] * 2
        for blueprint in blueprints:
            participant = Participant.objects.create(
                project=self.project,
                extra_data={},
                url_parameter={"class": self.classroom.url_id},
                start_time=timezone.now(),
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=blueprint,
                consent=True,
                data=self.watch_history_data["data"],
                data_extraction_state=DataDonation.DataExtractionState.DATA_EXTRACTED,
            )

        self.client.login(**self.base_creds)

        report_wh_url = reverse(
            "tiktok_class_report_wh_sections", kwargs={"url_id": self.classroom.url_id}
        )
        response = self.client.get(report_wh_url, **self.htmx_headers)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "reports/components/watch_history_stats_section.html"
        )

    def test_tiktok_example_report_wh_section(self):
        url = reverse("tiktok_example_report_wh_sections")
        response = self.client.get(url, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/tiktok/_watch_history_report_individual.html",
            "reports/components/watch_history_stats_section.html",
            "reports/components/watch_history_timeseries_section.html",
            "reports/components/watch_history_daily_heatmap_section.html",
            "reports/components/watch_history_fav_video_section.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)

    def test_tiktok_example_report_sh_section(self):
        url = reverse("tiktok_example_report_sh_sections")
        response = self.client.get(url, **self.htmx_headers)
        self.assertEqual(response.status_code, 200)

        required_templates = [
            "reports/tiktok/_search_history_report_individual.html",
            "reports/components/search_history_wordcloud.html",
        ]

        for template in required_templates:
            self.assertTemplateUsed(response, template)


class TestTikTokAlternateKeyExtraction(TestCase):
    """Tests that watch/search history extraction tolerates the alternate
    field-name variants ("Link"/"link", "Date"/"date", "searchterm"/
    "search_term") in addition to the primary "(L|l)ink"/"(D|d)ate"/
    "SearchTerm" keys, and that the extracted entries stay usable for
    interval-based statistics regardless of which variant was used.
    """

    def test_get_video_id_supports_all_link_key_variants(self):
        for key in ["(L|l)ink", "Link", "link"]:
            entry = {key: "https://www.tiktok.com/@/video/1234567890/"}
            self.assertEqual(tiktok_data_utils.get_video_id(entry), "1234567890")

    def test_get_video_id_returns_none_without_link_key(self):
        self.assertIsNone(tiktok_data_utils.get_video_id({}))

    def test_get_watch_date_supports_all_date_key_variants(self):
        for key in ["(D|d)ate", "Date", "date"]:
            entry = {key: "2024-01-01T12:00:00"}
            self.assertEqual(
                tiktok_data_utils.get_watch_date(entry), "2024-01-01T12:00:00"
            )

    def test_extract_watch_history_data_normalizes_alternate_keys(self):
        history = [
            [
                {
                    "Link": "https://www.tiktok.com/@/video/111/",
                    "Date": "2024-01-01T12:00:00",
                },
            ]
        ]
        result = tiktok_data_utils.extract_watch_history_data(history)
        self.assertEqual(result["video_ids"], ["111"])
        self.assertEqual(result["videos"][0]["date"], "2024-01-01T12:00:00")

    def test_extract_watch_history_data_handles_mixed_timezone_awareness(self):
        now = timezone.now()
        history = [
            [
                {
                    "Link": "https://www.tiktok.com/@/video/1/",
                    "Date": now.isoformat(),
                },
                {
                    "Link": "https://www.tiktok.com/@/video/2/",
                    "Date": (now - timedelta(days=1)).replace(tzinfo=None).isoformat(),
                },
            ]
        ]
        wh_data = tiktok_data_utils.extract_watch_history_data(history)
        self.assertEqual(len(wh_data["video_dates"]), 2)

        stats = tiktok_views.WatchHistorySectionsMixin.get_overall_statistics(
            wh_data["video_ids"], wh_data["video_dates"], n_donations=1
        )
        self.assertEqual(stats["n_videos"], 2)

    def test_extract_search_history_data_supports_all_term_key_variants(self):
        for key in ["SearchTerm", "searchterm", "search_term"]:
            history = [[{key: "cats", "date": "2024-01-01T12:00:00"}]]
            result = tiktok_data_utils.extract_search_history_data(history)
            self.assertEqual(result["search_terms"], ["cats"])

    def test_extract_search_history_data_normalizes_alternate_date_key(self):
        history = [[{"SearchTerm": "cats", "Date": "2024-01-01T12:00:00"}]]
        result = tiktok_data_utils.extract_search_history_data(history)
        self.assertEqual(result["searches"][0]["date"], "2024-01-01T12:00:00")

    def test_watch_history_interval_statistics_finds_alternate_date_key(self):
        """Regression test for a bug where get_interval_statistics filtered
        on the literal "(D|d)ate" key, so entries donated with the newly
        supported "Date"/"date" keys were silently excluded from the
        interval statistics, even though they're included in the overall
        stats."""
        now = timezone.now()
        history = [
            [
                {
                    "Link": "https://www.tiktok.com/@/video/1/",
                    "Date": (now - timedelta(days=1)).isoformat(),
                },
            ]
        ]
        wh_data = tiktok_data_utils.extract_watch_history_data(history)

        stats = tiktok_views.WatchHistorySectionsMixin.get_interval_statistics(
            wh_data["videos"],
            (now - timedelta(days=5), now),
            n_donations=1,
        )
        self.assertEqual(stats["n_videos"], 1)

    def test_search_history_interval_statistics_finds_alternate_date_key(self):
        now = timezone.now()
        history = [
            [
                {
                    "searchterm": "cats",
                    "date": (now - timedelta(days=1)).isoformat(),
                },
            ]
        ]
        sh_data = tiktok_data_utils.extract_search_history_data(history)

        stats = tiktok_views.SearchHistorySectionsMixin.get_search_history_statistics(
            sh_data["searches"],
            (now - timedelta(days=5), now),
            n_donations=1,
        )
        self.assertEqual(stats["n_searches_interval"], 1)


@override_settings(ALLOWED_REPORT_DOMAINS=["test.dev"])
class TestSendReportLinkEmail(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("send_report_link")

    def test_send_report_link(self):
        payload = json.dumps({"email": "example@mail.com", "link": "https://test.dev"})
        response = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_send_report_link_missing_email(self):
        payload = json.dumps({"link": "https://test.dev"})
        response = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_send_report_link_missing_link(self):
        payload = json.dumps({"email": "example@mail.com"})
        response = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_send_report_link_invalid_email(self):
        payload = json.dumps({"email": "example@mail", "link": "https://test.dev"})
        response = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 422)

    def test_send_report_link_invalid_link(self):
        payload = json.dumps(
            {"email": "example@mail.com", "link": "https://test.somethingelse"}
        )
        response = self.client.post(self.url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 403)
