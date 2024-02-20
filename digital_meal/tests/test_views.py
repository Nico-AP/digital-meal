from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from ..models import Classroom, Track

User = get_user_model()


class TestViews(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create User
        cls.base_creds = {
            'username': 'username', 'password': '123', 'email': 'username@mail.com'
        }
        cls.user = User.objects.create_user(**cls.base_creds)

        # Crate a track
        cls.track = Track.objects.create(
            name='trackname',
            active=True
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

    def test_project_expiration(self):
        self.client.login(**self.base_creds)

        # Test with regular project
        response = self.client.get(
            reverse('classroom-detail', args=[self.classroom_regular.pk]))
        self.assertEqual(response.status_code, 200)

        # Test with expired project
        response = self.client.get(
            reverse('classroom-detail', args=[self.classroom_expired.pk]))
        self.assertEqual(response.status_code, 302)
