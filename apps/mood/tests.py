from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import Plan, UserSubscription
from utils.constants import FEATURE_MOOD_BASIC, PLAN_LITE

User = get_user_model()


class MoodEntryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="mood@example.com", name="Mood", password="pass12345")
        plan, _ = Plan.objects.get_or_create(
            code=PLAN_LITE, defaults={"name": "Lite", "features": [FEATURE_MOOD_BASIC], "is_active": True}
        )
        UserSubscription.objects.create(user=self.user, plan=plan)
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_create_mood_entry(self):
        response = self.client.post("/api/mood/entries/", {"mood": "OK", "notes": "Tudo bem"}, format="json")
        self.assertEqual(response.status_code, 201)
