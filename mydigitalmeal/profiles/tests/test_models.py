import time

from django.contrib.auth import get_user_model
from django.test import TestCase

from mydigitalmeal.profiles.models import MDMProfile

User = get_user_model()


class TestMDMProfile(TestCase):
    def setUp(self):
        self.test_email = "test@example.com"
        self.user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
        )
        self.profile = MDMProfile.objects.create(user=self.user)

    def test_profile_activation(self):
        """Test that activating an already-activated profile doesn't break."""
        self.assertIsNone(self.profile.activated_at)

        self.profile.activate()
        activation_time = self.profile.activated_at

        time.sleep(1)

        self.profile.activate()
        self.assertEqual(activation_time, self.profile.activated_at)
