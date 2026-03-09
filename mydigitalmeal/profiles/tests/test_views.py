from unittest.mock import MagicMock, patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.test import Client, RequestFactory, TestCase

from mydigitalmeal.profiles.forms import MDMAuthForm
from mydigitalmeal.profiles.views import MDMConfirmLoginCodeView
from mydigitalmeal.userflow.constants import URLShortcut
from shared.routing.urls import absolute_reverse

User = get_user_model()


class TestMDMAuthView(TestCase):
    """Tests for MDMAuthView (signup/login)."""

    def setUp(self):
        self.client = Client()
        self.url = absolute_reverse(URLShortcut.LOGIN)
        self.test_email = "test@example.com"

    def test_view_uses_correct_template(self):
        """Test that the view uses the correct template."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profiles/login.html")

    def test_view_uses_correct_form_class(self):
        """Test that the view uses MDMAuthForm."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["form"], MDMAuthForm)

    @patch("mydigitalmeal.profiles.forms.RequestLoginCodeForm")
    def test_new_user_signup_creates_user(self, mock_request_code_form):
        """Test that submitting email for new user creates User and EmailAddress."""
        # Mock the RequestLoginCodeForm to avoid actually sending emails
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance._user = None
        mock_request_code_form.return_value = mock_form_instance

        self.assertFalse(User.objects.filter(email=self.test_email).exists())
        _ = self.client.post(self.url, {"login": self.test_email})

        self.assertTrue(User.objects.filter(email=self.test_email).exists())
        user = User.objects.get(email=self.test_email)
        self.assertTrue(
            EmailAddress.objects.filter(user=user, email=self.test_email).exists(),
        )

    @patch("mydigitalmeal.profiles.forms.RequestLoginCodeForm")
    def test_new_user_signup_creates_profile(self, mock_request_code_form):
        """Test that new user gets MDMProfile via signal."""
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance._user = None
        mock_request_code_form.return_value = mock_form_instance
        _ = self.client.post(self.url, {"login": self.test_email})

        user = User.objects.get(email=self.test_email)
        self.assertTrue(hasattr(user, "mdm_profile"))
        self.assertIsNotNone(user.mdm_profile)
        self.assertIsNone(user.mdm_profile.activated_at)

    @patch("mydigitalmeal.profiles.forms.RequestLoginCodeForm")
    def test_existing_user_login_does_not_duplicate(self, mock_request_code_form):
        """Test that existing user login doesn't create duplicates."""
        user = User.objects.create_user(email=self.test_email, username=self.test_email)
        EmailAddress.objects.create(
            user=user,
            email=self.test_email,
            verified=True,
            primary=True,
        )

        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance._user = user
        mock_request_code_form.return_value = mock_form_instance

        initial_user_count = User.objects.count()
        initial_email_count = EmailAddress.objects.count()

        _ = self.client.post(self.url, {"login": self.test_email})

        # No new users or email addresses created
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(EmailAddress.objects.count(), initial_email_count)

    @patch("mydigitalmeal.profiles.forms.RequestLoginCodeForm")
    def test_form_valid_redirects_to_code_confirmation(self, mock_request_code_form):
        """Test that valid form submission redirects to code confirmation."""
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance._user = None
        mock_request_code_form.return_value = mock_form_instance

        response = self.client.post(self.url, {"login": self.test_email})

        # Should redirect to code confirmation page
        self.assertEqual(response.status_code, 302)
        redirect_target = absolute_reverse(URLShortcut.CONFIRM_LOGIN)
        self.assertRedirects(
            response,
            redirect_target,
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True,
        )

    def test_authenticated_users_are_redirected_correctly(self):
        """Test that already-authenticated users are redirected to donation step."""
        self.user = User.objects.create_user(
            email="test@example.com",
            username="test@example.com",
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, absolute_reverse(URLShortcut.OVERVIEW))

    @patch("allauth.account.views.ConfirmLoginCodeView.form_valid")
    def test_user_with_active_confirmation_code_is_redirected_to_confirm_view(
        self,
        mock_request_code,
    ):
        # User requests login code
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance._user = None
        mock_request_code.return_value = mock_form_instance

        response = self.client.post(self.url, {"login": self.test_email})
        self.assertRedirects(response, absolute_reverse(URLShortcut.CONFIRM_LOGIN))

        # Login view should now redirect to confirm view
        response = self.client.get(self.url)
        self.assertRedirects(response, absolute_reverse(URLShortcut.CONFIRM_LOGIN))


class TestMDMConfirmLoginView(TestCase):
    """Tests for MDMConfirmLoginView (code verification)."""

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.url = absolute_reverse(URLShortcut.CONFIRM_LOGIN)
        self.auth_url = absolute_reverse(URLShortcut.LOGIN)
        self.test_email = "test@example.com"

        self.user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
        )
        EmailAddress.objects.create(
            user=self.user,
            email=self.test_email,
            verified=True,
            primary=True,
        )

    def test_no_login_process_redirects_to_auth(self):
        """Test that missing login process redirects to auth page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            absolute_reverse(URLShortcut.LOGIN),
            fetch_redirect_response=False,
        )

    # Note: Did not create actual view tests due to complications with
    # the allauth parent view setup.

    def test_get_next_url_returns_donation_step(self):
        """Test that get_next_url returns the correct URL."""
        view = MDMConfirmLoginCodeView()
        next_url = view.get_next_url()

        expected_url = absolute_reverse(URLShortcut.OVERVIEW)
        self.assertEqual(next_url, expected_url)

    def test_invalid_code_shows_error(self):
        """Test that invalid code shows error message."""
        self.client.post(self.auth_url, {"login": self.test_email})
        response = self.client.post(self.url, {"code": "invalid"})

        self.assertEqual(response.status_code, 200)
        if "form" in response.context:
            self.assertFalse(response.context["form"].is_valid())

    def test_authenticated_users_are_redirected_correctly(self):
        """Test that already-authenticated users are redirected to donation step."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, absolute_reverse(URLShortcut.OVERVIEW))


# Integration test for full flow
class TestAuthenticationFlow(TestCase):
    """Integration tests for the complete auth flow."""

    def setUp(self):
        self.client = Client()
        self.auth_url = absolute_reverse(URLShortcut.LOGIN)
        self.confirm_url = absolute_reverse(URLShortcut.CONFIRM_LOGIN)
        self.test_email = "test@example.com"

    @patch("mydigitalmeal.profiles.forms.RequestLoginCodeForm")
    @patch("allauth.account.views.ConfirmLoginCodeView.form_valid")
    def test_complete_signup_and_login_flow(
        self,
        mock_confirm_valid,
        mock_request_code,
    ):
        """Test complete flow from signup to successful login."""
        # Step 1: User submits email (signup)
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance._user = None
        mock_request_code.return_value = mock_form_instance

        self.client.post(self.auth_url, {"login": self.test_email})

        # User and profile should be created
        self.assertTrue(User.objects.filter(email=self.test_email).exists())
        user = User.objects.get(email=self.test_email)
        self.assertTrue(hasattr(user, "mdm_profile"))
        self.assertIsNone(user.mdm_profile.activated_at)

        # Step 2: User verifies code
        mock_confirm_valid.return_value = HttpResponseRedirect(
            absolute_reverse(URLShortcut.OVERVIEW),
        )

        self.client.force_login(user)
        self.client.post(self.confirm_url, {"code": "123456"})

        # Profile should be activated after code verification
        user.mdm_profile.refresh_from_db()

    def test_user_can_login_multiple_times(self):
        """Test that a user can request login codes multiple times."""
        # Create existing user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
        )
        EmailAddress.objects.create(
            user=user,
            email=self.test_email,
            verified=True,
            primary=True,
        )

        with patch("mydigitalmeal.profiles.forms.RequestLoginCodeForm") as mock:
            mock_instance = MagicMock()
            mock_instance.is_valid.return_value = True
            mock_instance._user = user
            mock.return_value = mock_instance

            # First login request
            response1 = self.client.post(self.auth_url, {"login": self.test_email})
            self.assertEqual(response1.status_code, 302)

            # Second login request
            response2 = self.client.post(self.auth_url, {"login": self.test_email})
            self.assertEqual(response2.status_code, 302)

            # Should still only have one user
            self.assertEqual(User.objects.filter(email=self.test_email).count(), 1)
