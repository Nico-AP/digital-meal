from unittest.mock import Mock, patch

from allauth.account.forms import RequestLoginCodeForm
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase

from mydigitalmeal.profiles.forms import MDMAuthForm

User = get_user_model()


class MDMAuthFormTestCase(TestCase):
    """Tests for the MDMAuthForm"""

    def setUp(self):
        """Set up test data"""
        self.test_email = "existing@example.com"
        self.existing_user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password="testpass123",
        )

    @patch.object(RequestLoginCodeForm, "is_valid")
    @patch.object(RequestLoginCodeForm, "__init__")
    def test_clean_without_password_with_email(self, mock_init, mock_is_valid):
        """Test _clean_without_password creates user and validates correctly"""
        mock_init.return_value = None
        mock_is_valid.return_value = True

        # Create a mock form with _user attribute
        mock_form_instance = Mock()
        mock_form_instance._user = self.existing_user

        with patch(
            "mydigitalmeal.profiles.forms.RequestLoginCodeForm",
            return_value=mock_form_instance,
        ):
            form = MDMAuthForm()
            form.cleaned_data = {}
            result = form._clean_without_password(email=self.test_email, phone=None)

            self.assertIsNotNone(result)
            self.assertEqual(form.user, self.existing_user)

    def test_clean_without_password_no_email_or_phone_adds_error(self):
        """Test that missing email and phone adds validation error"""
        form = MDMAuthForm()
        form.cleaned_data = {}

        result = form._clean_without_password(email=None, phone=None)

        self.assertIsNotNone(result)
        self.assertTrue(form.has_error("login"))

    def test_check_user_exists_returns_existing_user(self):
        """Test that _check_user_exists_or_create_new returns existing user"""
        form = MDMAuthForm()

        # Call the method
        form._check_user_exists_or_create_new(email=self.test_email)

        # Verify user wasn't created again
        self.assertEqual(User.objects.filter(email=self.test_email).count(), 1)

    def test_check_user_exists_creates_new_user(self):
        """Test that _check_user_exists_or_create_new creates user if not exists"""
        new_email = "brandnew@example.com"

        # Verify user doesn't exist
        self.assertFalse(User.objects.filter(email=new_email).exists())
        self.assertFalse(EmailAddress.objects.filter(email=new_email).exists())

        form = MDMAuthForm()
        form._check_user_exists_or_create_new(email=new_email)

        # Verify user was created
        self.assertTrue(User.objects.filter(email=new_email).exists())
        self.assertTrue(EmailAddress.objects.filter(email=new_email).exists())

    def test_newly_created_user_has_no_password(self):
        """Test that newly created users have unusable passwords"""
        new_email = "passwordless@example.com"

        form = MDMAuthForm()
        form._check_user_exists_or_create_new(email=new_email)

        created_user = User.objects.get(email=new_email)
        self.assertFalse(created_user.has_usable_password())

    def test_multiple_calls_dont_create_duplicate_users(self):
        email = "onceonly@example.com"

        form = MDMAuthForm()
        form._check_user_exists_or_create_new(email=email)
        form._check_user_exists_or_create_new(email=email)
        form._check_user_exists_or_create_new(email=email)

        # Verify only one user was created
        self.assertEqual(User.objects.filter(email=email).count(), 1)
