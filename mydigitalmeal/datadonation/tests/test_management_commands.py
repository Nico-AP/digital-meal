from io import StringIO

from ddm.datadonation.models import DonationBlueprint, FileUploader, ProcessingRule
from ddm.projects.models import DonationProject, ResearchProfile
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

User = get_user_model()


class TestCreateTikTokProjectCommand(TestCase):
    def setUp(self):
        user_mail = "some@mail.com"
        self.user_info = {
            "email": user_mail,
            "username": user_mail,
            "password": "testpassword",
        }

    def test_creates_all_objects(self):
        user = User.objects.create_user(**self.user_info)

        out = StringIO()
        args = [user.pk]
        call_command("create_tiktok_project", *args, stdout=out)

        self.assertIn(
            "successfully created",
            out.getvalue(),
        )
        self.assertEqual(DonationProject.objects.count(), 1)
        self.assertEqual(FileUploader.objects.count(), 1)
        self.assertEqual(DonationBlueprint.objects.count(), 12)
        self.assertEqual(ProcessingRule.objects.count(), 33)

    def test_handles_existing_project_gracefully_with_nonexisting_user(self):
        with self.assertRaises(CommandError):
            args = [10]
            call_command("create_tiktok_project", *args)

    def test_handles_existing_project_gracefully_with_existing_project(self):
        user = User.objects.create_user(**self.user_info)
        owner = ResearchProfile.objects.create(user=user)

        DonationProject.objects.create(
            name="test project",
            owner=owner,
            slug="tik-tok",
        )

        out = StringIO()
        args = [user.pk]
        call_command("create_tiktok_project", *args, stdout=out)
        self.assertIn(
            "already exists",
            out.getvalue(),
        )
        self.assertEqual(DonationProject.objects.count(), 1)
