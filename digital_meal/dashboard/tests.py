from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class DashboardViewTests(TestCase):
    """Tests for the DashboardView."""

    def setUp(self):
        """Set up test users."""
        # Create a regular user
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular_user@mail.com',
            password='testpass123'
        )

        # Create a staff user
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff_user@mail.com',
            password='testpass123',
            is_staff=True
        )

    def test_unauthenticated_user_redirect(self):
        """Test that unauthenticated users are redirected to login."""
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_non_staff_user_denied(self):
        """Test that authenticated non-staff users are denied access."""
        self.client.login(email='regular_user@mail.com', password='testpass123')
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_staff_user_access(self):
        """Test that staff users can access the dashboard."""
        self.client.login(email='staff_user@mail.com', password='testpass123')
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')

    def test_superuser_access(self):
        """Test that superusers can access the dashboard."""
        superuser = User.objects.create_superuser(
            username='superuser',
            password='testpass123',
            email='super@test.com',
            is_staff=True
        )
        self.client.login(email='super@test.com', password='testpass123')
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')
