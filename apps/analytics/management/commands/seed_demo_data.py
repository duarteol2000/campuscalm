from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from agenda.models import CalendarEvent, ReminderRule
from billing.models import Plan, UserSubscription
from content.models import GuidedContent
from mood.models import MoodEntry
from planner.models import Task
from semester.models import Assessment, Course, Semester
from utils.constants import (
    CONTENT_ANTI_PROCRASTINACAO,
    CONTENT_FOCO,
    CONTENT_PRE_PROVA,
    EVENT_ENTREGA,
    EVENT_PROVA,
    MOOD_BAD,
    MOOD_GOOD,
    MOOD_OK,
    MOOD_VERY_GOOD,
    PLAN_LITE,
)
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Cria dados de exemplo para o MVP"

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Email do usuario para popular dados")

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get("email")
        if email:
            user = User.objects.filter(email=email).first()
            if not user:
                self.stdout.write(self.style.ERROR("Usuario nao encontrado."))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("Nenhum usuario encontrado."))
                return

        plan = Plan.objects.filter(code=PLAN_LITE).first()
        if plan:
            UserSubscription.objects.get_or_create(user=user, defaults={"plan": plan})

        MoodEntry.objects.get_or_create(user=user, mood=MOOD_OK, defaults={"notes": "Inicio do semestre"})
        MoodEntry.objects.get_or_create(user=user, mood=MOOD_GOOD, defaults={"notes": "Boa semana"})
        MoodEntry.objects.get_or_create(user=user, mood=MOOD_BAD, defaults={"notes": "Cansaco"})
        MoodEntry.objects.get_or_create(user=user, mood=MOOD_VERY_GOOD, defaults={"notes": "Semana excelente"})

        Task.objects.get_or_create(
            user=user,
            title="Trabalho final",
            defaults={
                "description": "Entrega da disciplina X",
                "due_date": date.today() + timedelta(days=10),
                "stress_level": 3,
                "status": "TODO",
            },
        )
        Task.objects.get_or_create(
            user=user,
            title="Leitura cap. 3",
            defaults={
                "description": "Revisao para prova",
                "due_date": date.today() + timedelta(days=5),
                "stress_level": 2,
                "status": "DOING",
            },
        )
        Task.objects.get_or_create(
            user=user,
            title="Lista de exercicios",
            defaults={
                "description": "Praticar conteudos de logica",
                "due_date": date.today() + timedelta(days=3),
                "stress_level": 2,
                "status": "TODO",
            },
        )

        semester, _ = Semester.objects.get_or_create(
            user=user,
            name="2026.1",
            defaults={
                "start_date": date.today() - timedelta(days=20),
                "end_date": date.today() + timedelta(days=120),
            },
        )

        course_math, _ = Course.objects.get_or_create(
            semester=semester,
            title="Matematica Discreta",
            defaults={"teacher": "Prof. Silva", "credits": 4},
        )
        course_alg, _ = Course.objects.get_or_create(
            semester=semester,
            title="Algoritmos I",
            defaults={"teacher": "Prof. Souza", "credits": 4},
        )
        course_db, _ = Course.objects.get_or_create(
            semester=semester,
            title="Banco de Dados",
            defaults={"teacher": "Profa. Carla", "credits": 4},
        )

        Assessment.objects.get_or_create(
            course=course_math,
            title="Prova 1",
            defaults={"score": 7.5, "max_score": 10, "weight": 1, "date": date.today() + timedelta(days=7)},
        )
        Assessment.objects.get_or_create(
            course=course_math,
            title="Trabalho 1",
            defaults={"score": 8.0, "max_score": 10, "weight": 1, "date": date.today() + timedelta(days=14)},
        )
        Assessment.objects.get_or_create(
            course=course_alg,
            title="Trabalho 1",
            defaults={"score": 8.0, "max_score": 10, "weight": 1, "date": date.today() + timedelta(days=12)},
        )
        Assessment.objects.get_or_create(
            course=course_db,
            title="Prova 1",
            defaults={"score": 6.5, "max_score": 10, "weight": 1, "date": date.today() + timedelta(days=9)},
        )

        CalendarEvent.objects.get_or_create(
            user=user,
            title="Entrega Trabalho Final",
            defaults={"event_type": EVENT_ENTREGA, "start_at": timezone.now() + timedelta(days=9)},
        )
        CalendarEvent.objects.get_or_create(
            user=user,
            title="Prova Matematica",
            defaults={"event_type": EVENT_PROVA, "start_at": timezone.now() + timedelta(days=7)},
        )
        CalendarEvent.objects.get_or_create(
            user=user,
            title="Prova Banco de Dados",
            defaults={"event_type": EVENT_PROVA, "start_at": timezone.now() + timedelta(days=9)},
        )

        ReminderRule.objects.get_or_create(
            user=user,
            target_type="TASK",
            defaults={"remind_before_minutes": 1440, "channels": ["EMAIL"], "is_active": True},
        )

        GuidedContent.objects.get_or_create(
            title="Respiracao pre-prova",
            defaults={
                "category": CONTENT_PRE_PROVA,
                "duration_minutes": 8,
                "body_text": "Exercicio guiado de respiracao para antes da prova.",
                "is_premium": False,
            },
        )
        GuidedContent.objects.get_or_create(
            title="Anti-procrastinacao em 10 minutos",
            defaults={
                "category": CONTENT_ANTI_PROCRASTINACAO,
                "duration_minutes": 10,
                "body_text": "Passos curtos para iniciar tarefas e manter o ritmo.",
                "is_premium": False,
            },
        )
        GuidedContent.objects.get_or_create(
            title="Foco profundo 25min",
            defaults={
                "category": CONTENT_FOCO,
                "duration_minutes": 25,
                "body_text": "Sessao guiada de foco com pausas conscientes.",
                "is_premium": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("seed_demo_data: ok"))
