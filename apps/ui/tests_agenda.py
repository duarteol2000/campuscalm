from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from agenda.models import CalendarEvent
from utils.constants import EVENT_OUTRO

User = get_user_model()


class AgendaListHighlightTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="agenda-highlight@example.com",
            name="Agenda Highlight",
            password="pass12345",
        )
        self.event = CalendarEvent.objects.create(
            user=self.user,
            title="Reuniao de orientacao",
            event_type=EVENT_OUTRO,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=1),
            notes="descr",
        )

    def test_agenda_list_passes_highlight_event_to_context(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("ui-agenda-list"), {"highlight_event": self.event.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["highlight_event"], self.event.id)
        self.assertContains(response, f'id="event-row-{self.event.id}"')
        self.assertContains(response, "agenda-row-highlight")
