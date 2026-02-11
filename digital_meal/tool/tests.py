from datetime import timedelta

from ddm.datadonation.models import DataDonation
from ddm.participation.models import Participant
from ddm.projects.models import ResearchProfile, DonationProject
from ddm.questionnaire.models import QuestionnaireResponse, SingleChoiceQuestion
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from .forms import SimpleSignupForm
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

    def test_class_expiration(self):
        """
        Test that expired classrooms cannot be accessed and redirect to the
        "class expired" view.
        """
        self.client.login(**self.base_creds)

        # Test with active classroom.
        response = self.client.get(
            reverse('class_detail', args=[self.classroom_regular.url_id]))
        self.assertEqual(response.status_code, 200)

        # Test with expired classroom.
        response = self.client.get(
            reverse('class_detail', args=[self.classroom_expired.url_id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse(
            'class_expired', args=[self.classroom_expired.url_id]))

        # Test with test participation classroom.
        self.classroom_expired.is_test_participation_class = True
        self.classroom_expired.save()
        response = self.client.get(
            reverse('class_detail', args=[self.classroom_expired.url_id]))
        self.assertEqual(response.status_code, 200)
        self.classroom_expired.is_test_participation_class = False
        self.classroom_expired.save()


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

        usage_consent_question = SingleChoiceQuestion.objects.create(
            project=cls.project,
            name='DD Consent Question',
            variable_name='usage_dd_consent'
        )
        quest_consent_question = SingleChoiceQuestion.objects.create(
            project=cls.project,
            name='DD Consent Question',
            variable_name='quest_dd_consent'
        )

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

        usage_consent_key = usage_consent_question.get_response_keys()[0]
        quest_consent_key = quest_consent_question.get_response_keys()[0]

        cls.data_consent = {usage_consent_key: 1, quest_consent_key: 1}
        cls.data_no_consent = {usage_consent_key: 0, quest_consent_key: 0}
        cls.data_mixed_consent_a = {usage_consent_key: 1, quest_consent_key: 0}
        cls.data_mixed_consent_b = {usage_consent_key: 0, quest_consent_key: 1}
        cls.data_consent_missing = {'other_var': 1}

    def setUp(self):
        QuestionnaireResponse.objects.all().delete()

    def testCleanParticipantsExpiredWithConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_consent
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def testCleanParticipantsExpiredNoConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_no_consent
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 0)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 0)

    def testCleanParticipantsExpiredMixedConsentA(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_mixed_consent_a
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 0)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def testCleanParticipantsExpiredMixedConsentB(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_mixed_consent_b
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 0)

    def testCleanParticipantsExpiredMissingConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_consent_missing
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def testCleanParticipantsNotExpiredWithConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_consent
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def testCleanParticipantsNotExpiredNoConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_no_consent
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def testCleanParticipantsNotExpiredMissingConsent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_consent_missing
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=[],
            status=''
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command('clean_participants')
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)


class TestSimpleSignupForm(TestCase):

    def setUp(self):
        self.valid_data = {
            'first_name': 'Max',
            'name': 'Muster',
            'canton': 'AG',
            'school_name': 'Testschule',
            'email': 'test@example.com',
            'email2': 'test@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'mobile_phone_number': '',
        }

    def test_form_valid_without_honeypot(self):
        """Form should be valid when honeypot field is empty."""
        form = SimpleSignupForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalid_when_honeypot_filled(self):
        """Form should be invalid when honeypot field is filled (bot detected)."""
        data = {**self.valid_data, 'mobile_phone_number': '+41791234567'}
        form = SimpleSignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('mobile_phone_number', form.errors)

    def test_form_valid_when_honeypot_absent(self):
        """Form should be valid when honeypot field is not submitted at all."""
        data = {**self.valid_data}
        del data['mobile_phone_number']
        form = SimpleSignupForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_honeypot_not_in_field_order(self):
        """Honeypot field should not appear in the explicit field order."""
        form = SimpleSignupForm()
        self.assertNotIn('mobile_phone_number', form.field_order)
