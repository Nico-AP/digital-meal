from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse


User = get_user_model()


class WebsiteUrlTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_url(self):
        """Test that the home page URL returns a 200 status code."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


@override_settings(
    DDM_SETTINGS={'EMAIL_PERMISSION_CHECK':  r'.*(\.|@)test\.com$', }
)
class DDMMiddlewareTest(TestCase):
    def setUp(self):
        """Set up test users with different permission levels."""
        self.ddm_url = reverse('ddm_projects:list')

        # Create test users.
        self.superuser = User.objects.create_superuser(
            username='testadmin',
            email='admin@test.com',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='testpass123',
            email='staff@test.com',
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='regular@test.com',
        )
        self.client = Client()

    def test_unauthenticated_user_cannot_access_ddm(self):
        """Test that unauthenticated users get a 404 response."""
        response = self.client.get(self.ddm_url)
        self.assertEqual(response.status_code, 404)

    def test_normal_user_cannot_access_ddm(self):
        """Test that normal authenticated users get a 404 response."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.ddm_url)
        self.assertEqual(response.status_code, 404)

    def test_staff_can_access_ddm(self):
        """Test that staff users get a 200 response."""
        self.client.login(
            email='staff@test.com',
            username='staffuser',
            password='testpass123')
        response = self.client.get(self.ddm_url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_ddm(self):
        """Test that superusers get a 200 response."""
        self.client.login(
            email='admin@test.com',
            username='testadmin',
            password='testpass123')
        response = self.client.get(self.ddm_url)
        self.assertEqual(response.status_code, 200)
