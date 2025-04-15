from django.contrib.auth import get_user_model
from django.test import TestCase
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
