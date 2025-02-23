from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from ddm.datadonation.models import (
    FileUploader, DonationBlueprint, DataDonation
)
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile

from digital_meal.tool.models import Classroom, MainTrack

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

        # Crate a track
        cls.track = MainTrack.objects.create(
            name='trackname',
            active=True,
            ddm_path='https://127.0.0.1:8000/',
            ddm_project_id=cls.project.url_id
        )

        # Create Classroom - not expired
        cls.classroom_regular = Classroom.objects.create(
            owner=cls.user,
            name='regular class',
            track=cls.track,
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
            track=cls.track,
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

    def test_expired_clasroom_does_not_show_report(self):
        report_url = reverse(
            'class_report',
            kwargs={'url_id': self.classroom_expired.url_id}
        )
        expired_url = reverse(
            'class_expired',
            kwargs={'url_id': self.classroom_expired.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expired_url)

    def test_report_with_less_than_five_donations_does_not_show_report(self):
        report_url = reverse(
            'class_report',
            kwargs={'url_id': self.classroom_regular.url_id}
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_exception.html')

    def test_report_with_five_or_more_donations_shows_report(self):
        report_url = reverse(
            'class_report',
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
            'individual_report',
            kwargs={
                'url_id': self.classroom_regular.url_id,
                'participant_id': participant.external_id
            }
        )
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'reports/youtube/individual_report.html')
