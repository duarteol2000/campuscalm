from datetime import timedelta

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from agenda.models import CalendarEvent
from brain.models import CategoriaEmocional, InteracaoAluno
from brain.services.insights_service import build_dashboard_insights
from planner.models import Task
from utils.constants import EVENT_PROVA, TASK_DONE, TASK_TODO


class DashboardInsightsServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="insights@example.com",
            name="Insights",
            password="pass12345",
        )

    def _create_interaction(self, slug: str, hours_ago: int = 2):
        category = CategoriaEmocional.objects.get(slug=slug)
        interaction = InteracaoAluno.objects.create(
            user=self.user,
            mensagem_usuario=f"mensagem-{slug}",
            categoria_detectada=category,
            resposta_texto=f"resposta-{slug}",
            origem="widget",
        )
        timestamp = timezone.now() - timedelta(hours=hours_ago)
        InteracaoAluno.objects.filter(pk=interaction.pk).update(created_at=timestamp)

    def test_mood_fallback_uses_interacoes_when_no_mood_entries(self):
        for _ in range(3):
            self._create_interaction("stress")
        self._create_interaction("evolucao")

        data = build_dashboard_insights(self.user)

        self.assertEqual(data["mood_weekly_total"], 4)
        self.assertEqual(data["mood_most_common"], "Stress")

    def test_stress_avg_fallback_uses_interacoes_when_no_checkins(self):
        for _ in range(4):
            self._create_interaction("stress")
        for _ in range(2):
            self._create_interaction("social")

        data = build_dashboard_insights(self.user)

        self.assertEqual(data["stress_avg_week"], "6.7")

    def test_upcoming_count_counts_tasks_and_events_within_week(self):
        today = timezone.localdate()

        Task.objects.create(
            user=self.user,
            title="Tarefa valida",
            description="",
            due_date=today + timedelta(days=2),
            stress_level=3,
            status=TASK_TODO,
        )
        Task.objects.create(
            user=self.user,
            title="Tarefa fora da janela",
            description="",
            due_date=today + timedelta(days=10),
            stress_level=3,
            status=TASK_TODO,
        )
        Task.objects.create(
            user=self.user,
            title="Tarefa concluida",
            description="",
            due_date=today + timedelta(days=3),
            stress_level=2,
            status=TASK_DONE,
        )

        CalendarEvent.objects.create(
            user=self.user,
            title="Evento valido",
            event_type=EVENT_PROVA,
            start_at=timezone.now() + timedelta(days=1),
        )
        CalendarEvent.objects.create(
            user=self.user,
            title="Evento fora da janela",
            event_type=EVENT_PROVA,
            start_at=timezone.now() + timedelta(days=9),
        )

        data = build_dashboard_insights(self.user)

        self.assertEqual(data["upcoming_count"], 2)

    def test_absence_not_triggered_when_user_has_recent_task_or_event_context(self):
        today = timezone.localdate()
        task = Task.objects.create(
            user=self.user,
            title="Tarefa com prazo proximo",
            description="",
            due_date=today + timedelta(days=1),
            stress_level=3,
            status=TASK_TODO,
        )
        event = CalendarEvent.objects.create(
            user=self.user,
            title="Evento proximo",
            event_type=EVENT_PROVA,
            start_at=timezone.now() + timedelta(hours=8),
        )

        # Simula itens antigos criados no passado: ainda assim contam pelo prazo/inicio.
        old_created_at = timezone.now() - timedelta(days=10)
        Task.objects.filter(pk=task.pk).update(created_at=old_created_at)
        CalendarEvent.objects.filter(pk=event.pk).update(created_at=old_created_at)

        data = build_dashboard_insights(self.user)

        self.assertFalse(data["absence_alert_active"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_absence_email_sent_once_per_day_on_dashboard_refresh(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("ui-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("sentimos sua falta", mail.outbox[0].subject.lower())

        response = self.client.get(reverse("ui-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_absence_email_not_sent_when_recent_task_or_event_exists(self):
        today = timezone.localdate()
        task = Task.objects.create(
            user=self.user,
            title="Tarefa ativa",
            description="",
            due_date=today + timedelta(days=1),
            stress_level=2,
            status=TASK_TODO,
        )
        old_created_at = timezone.now() - timedelta(days=10)
        Task.objects.filter(pk=task.pk).update(created_at=old_created_at)

        self.client.force_login(self.user)
        response = self.client.get(reverse("ui-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

        response = self.client.get(reverse("ui-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
