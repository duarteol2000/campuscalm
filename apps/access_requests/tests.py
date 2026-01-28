from rest_framework.test import APITestCase

from utils.constants import FEATURE_EMAIL_NOTIFICATIONS, PLAN_PRO


class AccessRequestTriageTests(APITestCase):
    def test_triage_recommends_pro(self):
        payload = {
            "requester_email": "inst@example.com",
            "requester_type": "INDIVIDUAL",
            "wants_features": [FEATURE_EMAIL_NOTIFICATIONS],
        }
        response = self.client.post("/api/access/requests/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["recommended_plan"], PLAN_PRO)
