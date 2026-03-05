from datetime import timedelta
from unittest.mock import MagicMock, patch

from ddm.datadonation.models import DataDonation
from ddm.participation.models import Participant
from ddm.projects.models import DonationProject, ResearchProfile
from ddm.questionnaire.models import QuestionnaireResponse, SingleChoiceQuestion
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from digital_meal.tool.forms import SimpleSignupForm
from digital_meal.tool.models import BaseModule, Classroom, Teacher

User = get_user_model()


class TestViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            "username": "username",
            "password": "123",
            "email": "username@mail.com",
        }
        cls.user = User.objects.create_user(**cls.base_creds)

        # Crate a module
        cls.base_module = BaseModule.objects.create(
            name="module-name", active=True, report_prefix="youtube"
        )

        # Create Classroom - not expired
        cls.classroom_regular = Classroom.objects.create(
            owner=cls.user,
            name="regular class",
            base_module=cls.base_module,
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
            base_module=cls.base_module,
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

    def test_authenticated_access(self):
        """Test that authenticated users can access tool URLs."""
        self.client.login(**self.base_creds)
        for name, url in self.urls.items():
            response = self.client.get(url, follow=True)
            self.assertEqual(
                response.status_code,
                200,
                f"Authenticated user should be able to access {name}",
            )

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access tool URLs."""
        for name, url in self.urls.items():
            response = self.client.get(url)

            if name in ["class_detail"]:
                self.assertEqual(
                    response.status_code,
                    403,
                    f"Unauthenticated access to {url} should be restricted",
                )
            else:
                self.assertEqual(response.status_code, 302)
                redirect_url = response.url.split("?")[0]
                self.assertEqual(redirect_url, reverse("account_login"))

    def test_class_expiration(self):
        """
        Test that expired classrooms cannot be accessed and redirect to the
        "class expired" view.
        """
        self.client.login(**self.base_creds)

        # Test with active classroom.
        response = self.client.get(
            reverse("class_detail", args=[self.classroom_regular.url_id])
        )
        self.assertEqual(response.status_code, 200)

        # Test with expired classroom.
        response = self.client.get(
            reverse("class_detail", args=[self.classroom_expired.url_id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("class_expired", args=[self.classroom_expired.url_id])
        )

        # Test with test participation classroom.
        self.classroom_expired.is_test_participation_class = True
        self.classroom_expired.save()
        response = self.client.get(
            reverse("class_detail", args=[self.classroom_expired.url_id])
        )
        self.assertEqual(response.status_code, 200)
        self.classroom_expired.is_test_participation_class = False
        self.classroom_expired.save()


@override_settings(DAYS_TO_DONATION_DELETION=180)
class TestCleanParticipantsManagementCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            "username": "username",
            "password": "123",
            "email": "username@mail.com",
        }
        cls.user = User.objects.create_user(**cls.base_creds)
        cls.user_profile = ResearchProfile.objects.create(user=cls.user)
        cls.project = DonationProject.objects.create(
            name="Base Project", slug="base", owner=cls.user_profile
        )

        usage_consent_question = SingleChoiceQuestion.objects.create(
            project=cls.project,
            name="DD Consent Question",
            variable_name="usage_dd_consent",
        )
        quest_consent_question = SingleChoiceQuestion.objects.create(
            project=cls.project,
            name="DD Consent Question",
            variable_name="quest_dd_consent",
        )

        cls.expired_date = timezone.now() - timedelta(
            days=settings.DAYS_TO_DONATION_DELETION
        )
        cls.expired_participant = Participant.objects.create(
            project=cls.project,
            start_time=cls.expired_date,
            end_time=cls.expired_date,
            completed=True,
        )

        cls.valid_date = timezone.now() - timedelta(
            days=settings.DAYS_TO_DONATION_DELETION - 5
        )
        cls.non_expired_participant = Participant.objects.create(
            project=cls.project,
            start_time=cls.valid_date,
            end_time=cls.valid_date,
            completed=True,
        )

        usage_consent_key = usage_consent_question.get_response_keys()[0]
        quest_consent_key = quest_consent_question.get_response_keys()[0]

        cls.data_consent = {usage_consent_key: 1, quest_consent_key: 1}
        cls.data_no_consent = {usage_consent_key: 0, quest_consent_key: 0}
        cls.data_mixed_consent_a = {usage_consent_key: 1, quest_consent_key: 0}
        cls.data_mixed_consent_b = {usage_consent_key: 0, quest_consent_key: 1}
        cls.data_consent_missing = {"other_var": 1}

    def setUp(self):
        QuestionnaireResponse.objects.all().delete()

    def test_clean_participants_expired_with_consent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_consent,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def test_clean_participants_expired_no_consent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_no_consent,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 0)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 0)

    def test_clean_participants_expired_mixed_consent_a(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_mixed_consent_a,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 0)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def test_clean_participants_expired_mixed_consent_b(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_mixed_consent_b,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 0)

    def test_clean_participants_expired_missing_consent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=self.data_consent_missing,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def test_clean_participants_not_expired_with_consent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_consent,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def test_clean_participants_not_expired_no_consent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_no_consent,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)

    def test_clean_participants_not_expired_missing_consent(self):
        QuestionnaireResponse.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=self.data_consent_missing,
        )
        DataDonation.objects.create(
            project=self.project,
            participant=self.non_expired_participant,
            data=[],
            status="",
        )
        n_responses_before = QuestionnaireResponse.objects.all().count()
        n_donations_before = DataDonation.objects.all().count()
        call_command("clean_participants")
        n_responses_after = QuestionnaireResponse.objects.all().count()
        n_donations_after = DataDonation.objects.all().count()
        self.assertEqual(n_responses_before, 1)
        self.assertEqual(n_responses_after, 1)
        self.assertEqual(n_donations_before, 1)
        self.assertEqual(n_donations_after, 1)


class TestSimpleSignupForm(TestCase):
    def setUp(self):
        self.valid_data = {
            "first_name": "Max",
            "name": "Muster",
            "canton": "AG",
            "school_name": "Testschule",
            "email": "test@example.com",
            "email2": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
            "mobile_phone_number": "",
        }

    def test_form_valid_without_honeypot(self):
        """Form should be valid when honeypot field is empty."""
        form = SimpleSignupForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalid_when_honeypot_filled(self):
        """Form should be invalid when honeypot field is filled (bot detected)."""
        data = {**self.valid_data, "mobile_phone_number": "+41791234567"}
        form = SimpleSignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("mobile_phone_number", form.errors)

    def test_form_valid_when_honeypot_absent(self):
        """Form should be valid when honeypot field is not submitted at all."""
        data = {**self.valid_data}
        del data["mobile_phone_number"]
        form = SimpleSignupForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_honeypot_not_in_field_order(self):
        """Honeypot field should not appear in the explicit field order."""
        form = SimpleSignupForm()
        self.assertNotIn("mobile_phone_number", form.field_order)


class TestSimpleSignupFormFieldValidation(TestCase):
    def setUp(self):
        self.valid_data = {
            "first_name": "Max",
            "name": "Muster",
            "canton": "AG",
            "school_name": "Testschule",
            "email": "test@example.com",
            "email2": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }

    def test_form_invalid_when_canton_is_placeholder_value(self):
        # The first entry in the canton choices is ("", "bitte auswählen")
        data = {**self.valid_data, "canton": ""}
        form = SimpleSignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("canton", form.errors)

    def test_form_invalid_when_canton_is_unrecognised(self):
        data = {**self.valid_data, "canton": "XX"}
        form = SimpleSignupForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("canton", form.errors)


class TestSimpleSignupFormTeacherAlreadyExists(TestCase):
    """Unit tests for teacher_already_exists()."""

    BASE_DATA = {
        "first_name": "Max",
        "name": "Muster",
        "canton": "AG",
        "school_name": "Testschule",
        "password1": "SecurePass123!",
        "password2": "SecurePass123!",
    }

    @classmethod
    def setUpTestData(cls):
        cls.teacher_user = User.objects.create_user(
            username="teacher@example.com", password="pass", email="teacher@example.com"
        )
        Teacher.objects.create(
            user=cls.teacher_user, name="Muster", first_name="Max", canton="AG"
        )

    def _form_with_email(self, email):
        """Return an unbound form with cleaned_data pre-set to bypass email validation.

        teacher_already_exists() only reads cleaned_data['email'] — it has no
        dependency on the rest of the signup-form validation pipeline, so
        triggering is_valid() (which rejects already-registered addresses) would
        give a false negative and obscure what we are actually testing.
        """
        form = SimpleSignupForm()
        form.cleaned_data = {"email": email}
        return form

    def test_returns_true_when_teacher_with_email_exists(self):
        form = self._form_with_email("teacher@example.com")
        self.assertTrue(form.teacher_already_exists())

    def test_returns_false_when_no_teacher_with_email(self):
        form = self._form_with_email("nobody@example.com")
        self.assertFalse(form.teacher_already_exists())


class TestSimpleSignupFormTrySave(TestCase):
    """Unit tests for try_save() branching logic."""

    BASE_DATA = {
        "first_name": "Max",
        "name": "Muster",
        "canton": "AG",
        "school_name": "Testschule",
        "password1": "SecurePass123!",
        "password2": "SecurePass123!",
    }

    @classmethod
    def setUpTestData(cls):
        cls.teacher_user = User.objects.create_user(
            username="teacher", password="pass", email="teacher@example.com"
        )
        Teacher.objects.create(
            user=cls.teacher_user, name="Muster", first_name="Max", canton="AG"
        )

    def _valid_form(self, email):
        data = {**self.BASE_DATA, "email": email, "email2": email}
        form = SimpleSignupForm(data=data)
        form.is_valid()
        return form

    def test_calls_save_when_account_exists_but_no_teacher(self):
        form = self._valid_form("new@example.com")
        form.account_already_exists = True
        mock_user = MagicMock()
        mock_request = MagicMock()

        with patch.object(form, "save", return_value=mock_user) as mock_save:
            user, resp = form.try_save(mock_request)

        mock_save.assert_called_once_with(mock_request)
        self.assertIs(user, mock_user)
        self.assertIsNone(resp)

    def test_calls_save_when_account_does_not_exist(self):
        form = self._valid_form("new@example.com")
        form.account_already_exists = False
        mock_user = MagicMock()
        mock_request = MagicMock()

        with patch.object(form, "save", return_value=mock_user) as mock_save:
            user, resp = form.try_save(mock_request)

        mock_save.assert_called_once_with(mock_request)
        self.assertIs(user, mock_user)
        self.assertIsNone(resp)


class TestSimpleSignupFormSave(TestCase):
    """Unit tests for save() — flag management and delegation to create_teacher."""

    BASE_DATA = {
        "first_name": "Max",
        "name": "Muster",
        "canton": "AG",
        "school_name": "Testschule",
        "password1": "SecurePass123!",
        "password2": "SecurePass123!",
    }

    def _valid_form(self, email="new@example.com"):
        data = {**self.BASE_DATA, "email": email, "email2": email}
        form = SimpleSignupForm(data=data)
        form.is_valid()
        return form

    def test_returns_none_when_super_save_returns_none(self):
        form = self._valid_form()

        with patch("allauth.account.forms.SignupForm.save", return_value=None):
            result = form.save(MagicMock())

        print(result)
        self.assertIsNone(result)

    def test_calls_create_teacher_with_request_and_user(self):
        form = self._valid_form()
        mock_user = MagicMock()
        mock_request = MagicMock()

        with (
            patch("allauth.account.forms.SignupForm.save", return_value=mock_user),
            patch.object(form, "create_teacher") as mock_create,
        ):
            form.save(mock_request)

        mock_create.assert_called_once_with(mock_request, mock_user)

    def test_does_not_call_create_teacher_when_super_returns_none(self):
        form = self._valid_form()

        with (
            patch("allauth.account.forms.SignupForm.save", return_value=None),
            patch.object(form, "create_teacher") as mock_create,
        ):
            form.save(MagicMock())

        mock_create.assert_not_called()

    def test_returns_user_from_super_save(self):
        form = self._valid_form()
        mock_user = MagicMock()

        with (
            patch("allauth.account.forms.SignupForm.save", return_value=mock_user),
            patch.object(form, "create_teacher"),
        ):
            result = form.save(MagicMock())

        self.assertIs(result, mock_user)

    @override_settings(
        ACCOUNT_PREVENT_ENUMERATION=True,
        ACCOUNT_EMAIL_VERIFICATION="mandatory",
    )
    def test_user_password_is_set_for_existing_account_without_teacher(self):
        """Existing account with no Teacher profile should have its password updated."""
        user = User.objects.create_user(
            username="nopwd@example.com", email="nopwd@example.com"
        )
        user.set_unusable_password()
        user.save()

        new_password = self.BASE_DATA["password1"]
        post_data = {
            **self.BASE_DATA,
            "email": "nopwd@example.com",
            "email2": "nopwd@example.com",
        }
        form = self._valid_form(email="nopwd@example.com")

        request = RequestFactory().post("/accounts/signup/", data=post_data)
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()
        request.user = AnonymousUser()

        form.try_save(request)

        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
