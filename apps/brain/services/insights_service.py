from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

from agenda.models import CalendarEvent
from brain.models import InteracaoAluno
from mood.models import MoodEntry
from planner.models import Task
from pomodoro.models import PomodoroSession
from semester.models import SemesterCheckin
from utils.constants import TASK_DONE

LOOKBACK_DAYS = 7
ABSENCE_DAYS = 3
UPCOMING_WINDOW_DAYS = 7
UPCOMING_OVERLOAD_THRESHOLD = 4

MOOD_LABEL_FALLBACK = {
    "stress": "Stress",
    "evolucao": "Evolucao",
    "duvida": "Duvida",
    "social": "Social",
    "motivacao_baixa": "Motivacao baixa",
    "cansaco_mental": "Cansaco mental",
    "foco_alto": "Foco alto",
}

MSG_ABSENCE = (
    "Senti sua falta por aqui. Que tal fazer um check-in rapido hoje "
    "e escolher so uma tarefa pequena para comecar?"
)
MSG_OVERLOAD = (
    "Semana cheia de prazos. Vamos priorizar: escolha 1 tarefa mais urgente "
    "e quebre em um passo de 10 minutos."
)
MSG_STRESS = (
    "Percebi sinais de tensao na semana. Antes de acelerar, regula o corpo por "
    "1 minuto e comece pela tarefa mais simples."
)
MSG_EVOLUTION = (
    "Boa evolucao na semana. Mantem o ritmo: um passo pequeno hoje ja sustenta a consistencia."
)
MSG_DEFAULT = (
    "Semana em andamento. Escolha 1 foco do dia e avance 10 minutos. "
    "O resto fica mais leve depois."
)


def _seconds_until_end_of_day(now: datetime) -> int:
    local_now = timezone.localtime(now)
    next_day = (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((next_day - local_now).total_seconds()), 60)


def _slug_to_label(slug: str) -> str:
    if not slug:
        return "No data"
    if slug in MOOD_LABEL_FALLBACK:
        return MOOD_LABEL_FALLBACK[slug]
    return slug.replace("_", " ").title()


def _build_mood_data(user, week_ago: datetime) -> tuple[str, int]:
    mood_entries = MoodEntry.objects.filter(user=user, created_at__gte=week_ago)
    mood_total = mood_entries.count()
    if mood_total > 0:
        mood_counts = Counter(mood_entries.values_list("mood", flat=True))
        most_common_code = mood_counts.most_common(1)[0][0]
        mood_labels = dict(MoodEntry._meta.get_field("mood").choices)
        return mood_labels.get(most_common_code, str(most_common_code)), mood_total

    interactions = list(
        InteracaoAluno.objects.filter(user=user, created_at__gte=week_ago).select_related("categoria_detectada")
    )
    interactions_total = len(interactions)
    if interactions_total == 0:
        return "No data", 0

    category_counter = Counter(
        interaction.categoria_detectada.slug
        for interaction in interactions
        if interaction.categoria_detectada
    )
    if not category_counter:
        return "No data", interactions_total

    common_slug = category_counter.most_common(1)[0][0]
    return _slug_to_label(common_slug), interactions_total


def _build_stress_data(user, week_ago: datetime) -> tuple[str, float | None, float | None]:
    stress_values = list(
        SemesterCheckin.objects.filter(semester__user=user, created_at__gte=week_ago).values_list(
            "overall_stress", flat=True
        )
    )
    if stress_values:
        avg_stress_on_5 = sum(stress_values) / len(stress_values)
        avg_stress_on_10 = round(avg_stress_on_5 * 2, 1)
        return f"{avg_stress_on_10:.1f}", avg_stress_on_10, None

    interactions = InteracaoAluno.objects.filter(user=user, created_at__gte=week_ago)
    total = interactions.count()
    if total == 0:
        return "No data", None, None

    stress_count = interactions.filter(categoria_detectada__slug="stress").count()
    stress_ratio = stress_count / total
    stress_score = round(stress_ratio * 10, 1)
    return f"{stress_score:.1f}", stress_score, stress_ratio


def _build_focus_minutes_week(user, week_ago: datetime) -> int:
    minutes = PomodoroSession.objects.filter(user=user, started_at__gte=week_ago).values_list("focus_minutes", flat=True)
    return int(sum(minutes))


def _build_upcoming_count(user, now: datetime) -> int:
    today = timezone.localdate(now)
    next_week = today + timedelta(days=UPCOMING_WINDOW_DAYS)

    task_count = (
        Task.objects.filter(user=user, due_date__gte=today, due_date__lte=next_week)
        .exclude(status=TASK_DONE)
        .count()
    )
    event_count = CalendarEvent.objects.filter(
        user=user,
        start_at__date__gte=today,
        start_at__date__lte=next_week,
    ).count()
    return task_count + event_count


def _has_recent_real_activity(user, now: datetime) -> bool:
    """Detects activity using all real data sources, not just chat interactions."""
    recent_limit = now - timedelta(days=ABSENCE_DAYS)
    recent_limit_date = timezone.localdate(recent_limit)

    if InteracaoAluno.objects.filter(user=user, created_at__gte=recent_limit).exists():
        return True
    if MoodEntry.objects.filter(user=user, created_at__gte=recent_limit).exists():
        return True
    if SemesterCheckin.objects.filter(semester__user=user, created_at__gte=recent_limit).exists():
        return True
    if PomodoroSession.objects.filter(user=user, started_at__gte=recent_limit).exists():
        return True

    # Tasks/events count as activity if recently created OR temporally recent (due/start window).
    if Task.objects.filter(user=user, created_at__gte=recent_limit).exists():
        return True
    if Task.objects.filter(user=user, due_date__gte=recent_limit_date).exists():
        return True
    if CalendarEvent.objects.filter(user=user, created_at__gte=recent_limit).exists():
        return True
    if CalendarEvent.objects.filter(user=user, start_at__gte=recent_limit).exists():
        return True

    return False


def _compute_message_andamento(
    now: datetime,
    is_absent: bool,
    upcoming_count: int,
    stress_score: float | None,
    stress_ratio: float | None,
    evolucao_count_week: int,
    user_id: int,
) -> str:
    cache_key = f"campuscalm:insights_message:{user_id}:{timezone.localdate(now).strftime('%Y%m%d')}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if is_absent:
        selected = MSG_ABSENCE
    elif upcoming_count >= UPCOMING_OVERLOAD_THRESHOLD:
        selected = MSG_OVERLOAD
    elif (stress_score is not None and stress_score >= 6.0) or (stress_ratio is not None and stress_ratio >= 0.6):
        selected = MSG_STRESS
    elif evolucao_count_week >= 2:
        selected = MSG_EVOLUTION
    else:
        selected = MSG_DEFAULT

    cache.set(cache_key, selected, timeout=_seconds_until_end_of_day(now))
    return selected


def build_dashboard_insights(user, tz=None) -> dict:
    now = timezone.localtime(timezone.now(), tz) if tz else timezone.now()
    week_ago = now - timedelta(days=LOOKBACK_DAYS)

    mood_most_common, mood_weekly_total = _build_mood_data(user, week_ago)
    stress_avg_week, stress_score, stress_ratio = _build_stress_data(user, week_ago)
    focus_minutes_week = _build_focus_minutes_week(user, week_ago)
    upcoming_count = _build_upcoming_count(user, now)

    evolucao_count_week = InteracaoAluno.objects.filter(
        user=user,
        created_at__gte=week_ago,
        categoria_detectada__slug="evolucao",
    ).count()

    is_absent = not _has_recent_real_activity(user, now)

    message_andamento = _compute_message_andamento(
        now=now,
        is_absent=is_absent,
        upcoming_count=upcoming_count,
        stress_score=stress_score,
        stress_ratio=stress_ratio,
        evolucao_count_week=evolucao_count_week,
        user_id=user.id,
    )

    return {
        "message_andamento": message_andamento,
        "mood_most_common": mood_most_common,
        "mood_weekly_total": mood_weekly_total,
        "focus_minutes_week": focus_minutes_week,
        "stress_avg_week": stress_avg_week,
        "upcoming_count": upcoming_count,
        "absence_alert_active": message_andamento == MSG_ABSENCE,
    }
