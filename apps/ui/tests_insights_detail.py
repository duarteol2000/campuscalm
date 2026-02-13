from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class InsightsDetailViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="ui-insight@example.com",
            name="UI Insight",
            password="pass12345",
        )

    def test_mood_detail_requires_authentication(self):
        response = self.client.get(reverse("insights_detail"), {"type": "mood"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_mood_detail_returns_200_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("insights_detail"), {"type": "mood"})
        self.assertEqual(response.status_code, 200)

    def test_invalid_type_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("insights_detail"), {"type": "invalid"})
        self.assertEqual(response.status_code, 400)
