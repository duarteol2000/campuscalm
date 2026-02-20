from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from notifications.models import InAppNotification

User = get_user_model()


class InAppNotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="bell@example.com", name="Bell", password="pass12345")
        self.other = User.objects.create_user(email="other@example.com", name="Other", password="pass12345")
        self.client.force_login(self.user)

    def test_unread_count_and_mark_read(self):
        n1 = InAppNotification.objects.create(
            user=self.user,
            title="N1",
            body="body1",
            target_url="/tarefas/?highlight_task=1",
            is_read=False,
        )
        InAppNotification.objects.create(
            user=self.user,
            title="N2",
            body="body2",
            target_url="/tarefas/?highlight_task=2",
            is_read=False,
        )
        InAppNotification.objects.create(
            user=self.user,
            title="N3",
            body="body3",
            target_url="/tarefas/?highlight_task=3",
            is_read=False,
        )
        InAppNotification.objects.create(
            user=self.other,
            title="Other",
            body="other",
            target_url="/tarefas/",
            is_read=False,
        )

        count_response = self.client.get("/api/notifications/in-app/unread-count/")
        self.assertEqual(count_response.status_code, 200)
        self.assertEqual(count_response.data["unread_count"], 3)

        mark_response = self.client.post(f"/api/notifications/in-app/{n1.id}/mark-read/")
        self.assertEqual(mark_response.status_code, 200)
        self.assertEqual(mark_response.data["ok"], True)

        count_response_after = self.client.get("/api/notifications/in-app/unread-count/")
        self.assertEqual(count_response_after.status_code, 200)
        self.assertEqual(count_response_after.data["unread_count"], 2)

    def test_latest_limit(self):
        for index in range(8):
            InAppNotification.objects.create(
                user=self.user,
                title=f"N{index}",
                body=f"body{index}",
                target_url="/tarefas/",
                is_read=False,
            )

        response = self.client.get("/api/notifications/in-app/latest/?limit=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)
