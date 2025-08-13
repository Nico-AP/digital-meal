import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from ddm.datadonation.models import (
    FileUploader, DonationBlueprint, DataDonation
)
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile

from digital_meal.tool.models import Classroom, BaseModule

User = get_user_model()


class TestReports(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            'username': 'username',
            'password': '123',
            'email': 'username@mail.com'
        }
        cls.user = User.objects.create_user(**cls.base_creds)
        cls.research_profile = ResearchProfile.objects.create(user=cls.user)

        # Initialize a data donation project
        cls.project = DonationProject.objects.create(
            name='projectname',
            active=True,
            owner=cls.research_profile,
            contact_information='something',
            data_protection_statement='something',
            slug='slug'
        )

        cls.uploader = FileUploader.objects.create(
            project=cls.project,
            name='uploader',
            index=1,
            upload_type='zip file',
            combined_consent=True
        )

        cls.blueprint = DonationBlueprint.objects.create(
            project=cls.project,
            name='blueprintname',
            exp_file_format='json',
            file_uploader=cls.uploader,
        )

        # Crate a module
        cls.module = BaseModule.objects.create(
            name='module-name',
            active=True,
            ddm_path='https://127.0.0.1:8000/',
            ddm_project_id=cls.project.url_id,
            report_prefix='youtube_'
        )

        # Create Classroom - not expired
        cls.classroom_regular = Classroom.objects.create(
            owner=cls.user,
            name='regular class',
            base_module=cls.module,
            school_level='primary',
            school_year=10,
            subject='languages',
            instruction_format='regular'
        )

        # Create expired classroom
        cls.classroom_expired = Classroom.objects.create(
            owner=cls.user,
            name='regular class',
            expiry_date=timezone.now(),
            base_module=cls.module,
            school_level='primary',
            school_year=10,
            subject='languages',
            instruction_format='regular'
        )

        cls.urls = {
            'main': reverse('tool_main_page'),
            'class_create': reverse('class_create'),
            'class_detail': reverse(
                'class_detail',
                kwargs={'url_id': cls.classroom_regular.url_id}),
            'profile': reverse('profile'),
        }

    def setUp(self):
        self.client.login(**self.base_creds)

    def test_expired_classroom_does_not_show_report(self):
        report_url = reverse(
            'youtube_class_report',
            kwargs={'url_id': self.classroom_expired.url_id}
        )
        expired_url = reverse(
            'class_expired',
            kwargs={'url_id': self.classroom_expired.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expired_url)

    def test_class_report_is_accessible_by_owner(self):
        report_url = reverse(
            'youtube_class_report',
            kwargs={'url_id': self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)

    def test_class_report_is_not_accessible_when_logged_out(self):
        self.client.logout()
        login_url = reverse('account_login')
        report_url = reverse(
            'youtube_class_report',
            kwargs={'url_id': self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, login_url + f'?next={report_url}')

    def test_class_report_is_not_accessible_to_non_owner(self):
        self.client.logout()
        test_creds = {
            'username': 'test_user',
            'password': '123',
            'email': 'testuser@mail.com'
        }
        User.objects.create_user(**test_creds)
        self.client.login(**test_creds)
        report_url = reverse(
            'youtube_class_report',
            kwargs={'url_id': self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 403)

    def test_report_with_less_than_five_donations_does_not_show_report(self):
        report_url = reverse(
            'youtube_class_report',
            kwargs={'url_id': self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_exception.html')

    def test_report_with_five_or_more_donations_shows_report(self):
        report_url = reverse(
            'youtube_class_report',
            kwargs={'url_id': self.classroom_regular.url_id}
        )
        # Create 5 donations
        for _ in range(5):
            participant = Participant.objects.create(
                project=self.project,
                extra_data={
                    'url_param': {'class': self.classroom_regular.url_id}
                },
                start_time=timezone.now(),
            )
            DataDonation.objects.create(
                project=self.project,
                participant=participant,
                blueprint=self.blueprint,
                consent=True,
                data='{"data": "somedata"}',
                status='success'
            )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/youtube/class_report.html')

    def test_individual_report(self):
        # Create donation
        participant = Participant.objects.create(
            project=self.project,
            extra_data={
                'url_param': {'class': self.classroom_regular.url_id}
            },
            start_time=timezone.now(),
            end_time=timezone.now()
        )
        DataDonation.objects.create(
            project=self.project,
            participant=participant,
            blueprint=self.blueprint,
            consent=True,
            data='{"data": "somedata"}',
            status='success'
        )
        report_url = reverse(
            'youtube_individual_report',
            kwargs={
                'url_id': self.classroom_regular.url_id,
                'participant_id': participant.external_id
            }
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'reports/youtube/individual_report.html')

    def test_youtube_example_report(self):
        url = reverse('youtube_example_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'reports/youtube/example_report.html')

    def test_tiktok_example_report(self):
        url = reverse('tiktok_example_report')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'reports/tiktok/example_report.html')


@override_settings(ALLOWED_REPORT_DOMAINS=['test.dev'])
class TestSendReportLinkEmail(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('send_report_link')

    def test_send_report_link(self):
        payload = json.dumps({
            'email': 'example@mail.com',
            'link': 'https://test.dev'
        })
        response = self.client.post(
            self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_send_report_link_missing_email(self):
        payload = json.dumps({'link': 'https://test.dev'})
        response = self.client.post(
            self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_send_report_link_missing_link(self):
        payload = json.dumps({'email': 'example@mail.com'})
        response = self.client.post(
            self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_send_report_link_invalid_email(self):
        payload = json.dumps({
            'email': 'example@mail',
            'link': 'https://test.dev'
        })
        response = self.client.post(
            self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 422)

    def test_send_report_link_invalid_link(self):
        payload = json.dumps({
            'email': 'example@mail.com',
            'link': 'https://test.somethingelse'
        })
        response = self.client.post(
            self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 403)
