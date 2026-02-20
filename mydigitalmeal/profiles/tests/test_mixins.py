from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from mydigitalmeal.profiles.mixins import LoginAndProfileRequiredMixin
from mydigitalmeal.profiles.models import MDMProfile

User = get_user_model()


class TestLoginAndProfileRequiredMixin(TestCase):
    def setUp(self):
        class TestView(LoginAndProfileRequiredMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("Success")

        self.view = TestView.as_view()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_accessible_to_authenticated_user(self):
        request = RequestFactory().get("/")
        request.user = self.user

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Success")

    def test_not_accessible_to_unauthenticated_user(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        response = self.view(request)

        self.assertEqual(response.status_code, 302)

    def test_creates_profile_for_authenticated_user_if_not_existing(self):
        request = RequestFactory().get("/")
        request.user = self.user

        self.assertFalse(MDMProfile.objects.filter(user=self.user).exists())

        response = self.view(request)

        self.assertTrue(MDMProfile.objects.filter(user=self.user).exists())
        self.assertEqual(response.status_code, 200)

    def test_for_authenticated_user_with_existing_profile(self):
        existing_profile = MDMProfile.objects.create(user=self.user)

        request = RequestFactory().get("/")
        request.user = self.user

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MDMProfile.objects.filter(user=self.user).count(), 1)
        self.assertEqual(request.mdm_profile, existing_profile)
