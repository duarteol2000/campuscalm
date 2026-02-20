from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from planner.models import Task
from utils.constants import TASK_TODO

User = get_user_model()


class TaskListHighlightTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="task-highlight@example.com",
            name="Task Highlight",
            password="pass12345",
        )
        self.task = Task.objects.create(
            user=self.user,
            title="Revisar calculo",
            description="descr",
            due_date=timezone.localdate() + timedelta(days=1),
            stress_level=3,
            status=TASK_TODO,
        )

    def test_task_list_passes_highlight_task_to_context(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("ui-task-list"), {"highlight_task": self.task.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["highlight_task"], self.task.id)
        self.assertContains(response, f'id="task-row-{self.task.id}"')
        self.assertContains(response, "task-row-highlight")

    def test_task_edit_prefills_due_date_for_html_date_input(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("ui-task-edit", kwargs={"pk": self.task.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="date"')
        self.assertContains(response, f'value="{self.task.due_date:%Y-%m-%d}"')
