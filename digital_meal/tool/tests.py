from datetime import timedelta

from ddm.participation.models import Participant
from ddm.projects.models import ResearchProfile, DonationProject
from ddm.questionnaire.models import QuestionnaireResponse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from .models import Classroom, BaseModule

User = get_user_model()


class TestViews(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            'username': 'username',
            'password': '123',
            'email': 'username@mail.com'
        }
        cls.user = User.objects.create_user(**cls.base_creds)

        # Crate a module
        cls.base_module = BaseModule.objects.create(
            name='module-name',
            active=True,
            report_prefix='youtube'
        )

        # Create Classroom - not expired
        cls.classroom_regular = Classroom.objects.create(
            owner=cls.user,
            name='regular class',
            base_module=cls.base_module,
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
            base_module=cls.base_module,
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

    def test_authenticated_access(self):
        """Test that authenticated users can access tool URLs."""
        self.client.login(**self.base_creds)
        for name, url in self.urls.items():
            response = self.client.get(url, follow=True)
            self.assertEqual(
                response.status_code, 200,
                f'Authenticated user should be able to access {name}'
            )

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access tool URLs."""
        for name, url in self.urls.items():
            response = self.client.get(url)

            if name in ['class_detail']:
                self.assertEqual(
                    response.status_code, 403,
                    f'Unauthenticated access to {url} should be restricted'
                )
            else:
                self.assertEqual(response.status_code, 302)
                redirect_url = response.url.split('?')[0]
                self.assertEqual(redirect_url, reverse('account_login'))

    def test_project_expiration(self):
        """
        Test that expired projects cannot be accessed and redirect to the
        "project expired" view.
        """
        self.client.login(**self.base_creds)

        # Test with regular project
        response = self.client.get(
            reverse('class_detail', args=[self.classroom_regular.url_id]))
        self.assertEqual(response.status_code, 200)

        # Test with expired project
        response = self.client.get(
            reverse('class_detail', args=[self.classroom_expired.url_id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse(
            'class_expired', args=[self.classroom_expired.url_id]))



@override_settings(DAYS_TO_DONATION_DELETION=180)
class TestCleanParticipantsManagementCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            'username': 'username',
            'password': '123',
            'email': 'username@mail.com'
        }
        cls.user = User.objects.create_user(**cls.base_creds)
        cls.user_profile = ResearchProfile.objects.create(user=cls.user)
        cls.project = DonationProject.objects.create(
            name='Base Project', slug='base', owner=cls.user_profile)

        cls.expired_date = timezone.now() - timedelta(days=settings.DAYS_TO_DONATION_DELETION)
        cls.expired_participant = Participant.objects.create(
            project=cls.project,
            start_time=cls.expired_date,
            end_time=cls.expired_date,
            completed=True
        )

        cls.valid_date = timezone.now() - timedelta(days=settings.DAYS_TO_DONATION_DELETION - 5)
        cls.non_expired_participant = Participant.objects.create(
            project=cls.project,
            start_time=cls.valid_date,
            end_time=cls.valid_date,
            completed=True
        )

        cls.data_consent = {'dd_consent': 1}
        cls.data_no_consent = {'dd_consent': 0}
        cls.data_consent_missing = {'other_var': 1}

    def setUp(self):
        QuestionnaireResponse.objects.all().delete()

    def testCleanParticipantsExpiredWithConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_consent
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)

    def testCleanParticipantsExpiredNoConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_no_consent
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 0)

    def testCleanParticipantsExpiredMissingConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_consent_missing
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 0)

    def testCleanParticipantsNotExpiredWithConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_consent
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)

    def testCleanParticipantsNotExpiredNoConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_no_consent
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)

    def testCleanParticipantsNotExpiredMissingConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_consent_missing
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
