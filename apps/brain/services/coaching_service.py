from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from django.core.mail import send_mail
from django.db.models import Avg, Max
from django.utils import timezone
from django.conf import settings

from accounts.models import UserProfile
from agenda.models import CalendarEvent, Reminder
from brain.models import InteracaoAluno, WeeklyCoachingAssessment
from mood.models import MoodEntry
from planner.models import Task
from pomodoro.models import PomodoroSession
from semester.models import SemesterCheckin
from utils.constants import MOOD_BAD, MOOD_GOOD, MOOD_OK, MOOD_VERY_BAD, MOOD_VERY_GOOD, TASK_DONE

logger = logging.getLogger(__name__)

MOOD_SCORE_MAP_0_10 = {
    MOOD_VERY_BAD: 2,
    MOOD_BAD: 4,
    MOOD_OK: 6,
    MOOD_GOOD: 8,
    MOOD_VERY_GOOD: 10,
}


@dataclass(frozen=True)
class WeeklyCoachingScoreResult:
    week_reference: datetime.date
    score: int
    risk_level: str
    metrics: dict


def get_week_reference(today=None):
    local_today = today or timezone.localdate()
    return local_today - timedelta(days=local_today.weekday())


def classify_weekly_risk(score: int) -> str:
    score = max(0, min(int(score), 100))
    if score >= 80:
        return WeeklyCoachingAssessment.RISK_HIGH
    if score >= 60:
        return WeeklyCoachingAssessment.RISK_MODERATE
    if score >= 30:
        return WeeklyCoachingAssessment.RISK_LOW
    return WeeklyCoachingAssessment.RISK_STABLE


def _latest_activity_at(user):
    timestamps = []

    brain_last = InteracaoAluno.objects.filter(user=user).aggregate(value=Max("created_at"))["value"]
    mood_last = MoodEntry.objects.filter(user=user).aggregate(value=Max("created_at"))["value"]
    task_last = Task.objects.filter(user=user).aggregate(value=Max("created_at"))["value"]
    event_last = CalendarEvent.objects.filter(user=user).aggregate(value=Max("created_at"))["value"]
    reminder_last = Reminder.objects.filter(user=user).aggregate(value=Max("created_at"))["value"]
    pomodoro_last_started = PomodoroSession.objects.filter(user=user).aggregate(value=Max("started_at"))["value"]
    pomodoro_last_ended = PomodoroSession.objects.filter(user=user).aggregate(value=Max("ended_at"))["value"]

    semester_checkin_last = SemesterCheckin.objects.filter(semester__user=user).aggregate(value=Max("created_at"))["value"]

    for value in (
        brain_last,
        mood_last,
        task_last,
        event_last,
        reminder_last,
        pomodoro_last_started,
        pomodoro_last_ended,
        semester_checkin_last,
    ):
        if value:
            timestamps.append(value)

    if not timestamps:
        return None
    return max(timestamps)


def _days_without_activity(user, now=None):
    current_time = now or timezone.now()
    latest = _latest_activity_at(user)
    if latest is None:
        return 999
    delta = timezone.localtime(current_time).date() - timezone.localtime(latest).date()
    return max(delta.days, 0)


def _overdue_tasks_count(user, today=None):
    current_date = today or timezone.localdate()
    return Task.objects.filter(user=user, due_date__lt=current_date).exclude(status=TASK_DONE).count()


def _weekly_mood_average_0_10(user, now=None):
    current_time = now or timezone.now()
    week_start = current_time - timedelta(days=7)
    moods = MoodEntry.objects.filter(user=user, created_at__gte=week_start).values_list("mood", flat=True)
    scores = [MOOD_SCORE_MAP_0_10.get(code) for code in moods if code in MOOD_SCORE_MAP_0_10]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _weekly_stress_average_0_10(user, now=None):
    current_time = now or timezone.now()
    week_start = current_time - timedelta(days=7)

    checkin_avg = SemesterCheckin.objects.filter(
        semester__user=user,
        created_at__gte=week_start,
    ).aggregate(avg=Avg("overall_stress"))["avg"]
    if checkin_avg is not None:
        return round(float(checkin_avg) * 2.0, 1)  # escala 1-5 -> aprox 0-10

    total_interactions = InteracaoAluno.objects.filter(user=user, created_at__gte=week_start).count()
    if total_interactions == 0:
        return None
    stress_interactions = InteracaoAluno.objects.filter(
        user=user,
        created_at__gte=week_start,
        categoria_detectada__slug="stress",
    ).count()
    return round((stress_interactions / total_interactions) * 10.0, 1)


def calculate_weekly_score(user, now=None) -> WeeklyCoachingScoreResult:
    current_time = now or timezone.now()
    week_reference = get_week_reference(timezone.localdate(current_time))

    days_without_activity = _days_without_activity(user, current_time)
    overdue_tasks = _overdue_tasks_count(user, timezone.localdate(current_time))
    mood_average = _weekly_mood_average_0_10(user, current_time)
    stress_average = _weekly_stress_average_0_10(user, current_time)

    score = 0
    if days_without_activity >= 3:
        score += 25
    if overdue_tasks >= 2:
        score += 25
    if mood_average is not None and mood_average < 5:
        score += 25
    if stress_average is not None and stress_average > 7:
        score += 25

    score = max(0, min(score, 100))
    risk_level = classify_weekly_risk(score)

    metrics = {
        "days_without_activity": days_without_activity,
        "overdue_tasks": overdue_tasks,
        "mood_average_0_10": mood_average,
        "stress_average_0_10": stress_average,
    }
    return WeeklyCoachingScoreResult(
        week_reference=week_reference,
        score=score,
        risk_level=risk_level,
        metrics=metrics,
    )


def generate_coach_email(user, risk_level):
    risk_level = (risk_level or "").upper()
    first_name = (getattr(user, "name", "") or "").strip().split(" ")[0] or "Oi"

    templates = {
        WeeklyCoachingAssessment.RISK_LOW: (
            "Pequeno ajuste estrategico para sua semana",
            (
                f"Ola, {first_name}.\n\n"
                "Percebi sinais leves de sobrecarga.\n"
                "Vamos simplificar:\n\n"
                "1) Escolha 1 tarefa importante para hoje.\n"
                "2) Defina 1 meta clara de 10 a 15 minutos.\n"
                "3) Ignore o restante ate concluir esse primeiro passo.\n\n"
                "Voce nao precisa resolver tudo hoje.\n"
                "Eu estou acompanhando seu progresso.\n\n"
                "— CampusCalm"
            ),
        ),
        WeeklyCoachingAssessment.RISK_MODERATE: (
            "Uma pequena pausa estrategica para seu semestre",
            (
                f"Ola, {first_name}.\n\n"
                "Percebemos que sua semana pode ter sido mais intensa do que o habitual.\n\n"
                "Alguns sinais de sobrecarga ou queda de ritmo apareceram nos seus registros recentes.\n\n"
                "Isso acontece — especialmente em fases mais exigentes do semestre.\n\n"
                "1) Escolha apenas 1 tarefa importante para organizar hoje.\n"
                "2) Reserve 25 minutos de foco total (sem distracoes).\n"
                "3) Ajuste uma prioridade para amanha.\n\n"
                "Pequenos ajustes consistentes costumam mudar a direcao da semana.\n\n"
                "—\n"
                "Equipe CampusCalm\n"
                "Assistente Academico Inteligente\n\n"
                "Este acompanhamento foi enviado com base nos seus registros recentes no CampusCalm.\n"
                "Voce pode desativar o acompanhamento inteligente nas configuracoes do seu perfil."
            ),
        ),
        WeeklyCoachingAssessment.RISK_HIGH: (
            "Vamos aliviar a semana com um plano curto",
            (
                f"Ola, {first_name}.\n\n"
                "Percebi sinais fortes de sobrecarga nesta semana.\n"
                "Vamos focar no que ajuda agora, sem peso extra:\n\n"
                "1) Escolha a entrega mais urgente e faça o menor passo possivel.\n"
                "2) Adie o que nao e prioridade para depois.\n"
                "3) Faça uma pausa curta de regulacao antes de continuar.\n\n"
                "Voce nao precisa resolver tudo de uma vez.\n"
                "Um passo claro ja muda a semana.\n\n"
                "— CampusCalm"
            ),
        ),
    }

    default_subject = "Acompanhamento semanal CampusCalm"
    default_body = (
        f"Ola, {first_name}.\n\n"
        "Estou acompanhando sua semana.\n"
        "Se precisar, volte ao painel e escolha uma acao pequena para hoje.\n\n"
        "— CampusCalm"
    )
    return templates.get(risk_level, (default_subject, default_body))


def send_coaching_email(user, risk_level) -> bool:
    if not user or not user.is_active or not user.email:
        return False
    subject, body = generate_coach_email(user, risk_level)
    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info("weekly_coaching_email_sent user_id=%s risk=%s", user.id, risk_level)
    return True


def is_coaching_eligible(user, allow_all=False) -> bool:
    if not user or not user.is_active:
        return False
    if allow_all:
        return True
    profile = getattr(user, "profile", None)
    if not profile:
        return False
    return bool(profile.coach_enabled or profile.plan in {UserProfile.PLAN_PRO, UserProfile.PLAN_PAID})
