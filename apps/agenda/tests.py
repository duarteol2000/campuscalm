from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import Plan, UserSubscription
from utils.constants import FEATURE_IN_APP_REMINDERS, FEATURE_PLANNER_BASIC, PLAN_LITE

User = get_user_model()


class ReminderGenerationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="agenda@example.com", name="Agenda", password="pass12345")
        plan, _ = Plan.objects.get_or_create(
            code=PLAN_LITE,
            defaults={
                "name": "Lite",
                "features": [FEATURE_PLANNER_BASIC, FEATURE_IN_APP_REMINDERS],
                "is_active": True,
            },
        )
        UserSubscription.objects.create(user=self.user, plan=plan)
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_task_create_and_generate_reminders(self):
        task_payload = {
            "title": "Trabalho",
            "description": "Entrega final",
            "due_date": date.today().isoformat(),
            "stress_level": 3,
            "status": "TODO",
        }
        task_response = self.client.post("/api/planner/tasks/", task_payload, format="json")
        self.assertEqual(task_response.status_code, 201)

        rule_payload = {
            "target_type": "TASK",
            "remind_before_minutes": 60,
            "channels": ["EMAIL"],
            "is_active": True,
        }
        rule_response = self.client.post("/api/agenda/reminder-rules/", rule_payload, format="json")
        self.assertEqual(rule_response.status_code, 201)

        generate_response = self.client.post("/api/agenda/generate-reminders/", {}, format="json")
        self.assertEqual(generate_response.status_code, 200)
        self.assertIn("created", generate_response.data)
