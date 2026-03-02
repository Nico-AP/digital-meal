from django.test import TestCase
from django.urls import reverse


class InfoPagesViewTests(TestCase):
    def test_about_page(self):
        url = reverse("infopages:about")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_background_page(self):
        url = reverse("infopages:background")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_data_protection_page(self):
        url = reverse("infopages:data_protection")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_tos_page(self):
        url = reverse("infopages:tos")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dps_page(self):
        url = reverse("infopages:dps")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
