from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db.models import Max, Sum
from django.utils import timezone

from learning.models import AcademicDisciplineScore, EmotionalCheckin, StudySession, StudyTask


@dataclass(frozen=True)
class ScoreBand:
    min_value: int
    max_value: int
    label: str


SCORE_BANDS = [
    ScoreBand(0, 300, "baixa disciplina"),
    ScoreBand(301, 500, "irregular"),
    ScoreBand(501, 700, "organizado"),
    ScoreBand(701, 850, "disciplinado"),
    ScoreBand(851, 1000, "mestre da consistência"),
]


def clamp_score(value: int, min_value: int = 0, max_value: int = 1000) -> int:
    return max(min_value, min(max_value, int(value)))


def classify_score(score: int) -> str:
    normalized = clamp_score(score)
    for band in SCORE_BANDS:
        if band.min_value <= normalized <= band.max_value:
            return band.label
    return SCORE_BANDS[-1].label


def _to_date(value: datetime | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return timezone.localtime(value).date()
    return value


def _window_date_bounds(reference: date, days: int) -> tuple[date, date]:
    start = reference - timedelta(days=days - 1)
    return start, reference


def _sessions_days_in_window(student_id: int, institution_id: int, reference: date, days: int) -> set[date]:
    start, end = _window_date_bounds(reference, days)
    return set(
        StudySession.objects.filter(
            student_id=student_id,
            institution_id=institution_id,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).values_list("created_at__date", flat=True)
    )


def _sessions_in_window(student_id: int, institution_id: int, reference: date, days: int) -> int:
    start, end = _window_date_bounds(reference, days)
    return int(
        StudySession.objects.filter(
            student_id=student_id,
            institution_id=institution_id,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).count()
    )


def _minutes_studied_in_window(student_id: int, institution_id: int, reference: date, days: int) -> int:
    start, end = _window_date_bounds(reference, days)
    start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end, datetime.max.time()))
    total = (
        StudySession.objects.filter(
            student_id=student_id,
            institution_id=institution_id,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        ).aggregate(total_minutes=Sum("duration_minutes"))["total_minutes"]
        or 0
    )
    return int(total)


def _max_streak(days: set[date]) -> int:
    ordered = sorted(set(days))
    if not ordered:
        return 0
    longest = 1
    current = 1
    for idx in range(1, len(ordered)):
        if (ordered[idx] - ordered[idx - 1]).days == 1:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 1
    return longest


def _completed_tasks_on_time(student_id: int, institution_id: int) -> int:
    total = 0
    for due_date, completed_at in StudyTask.objects.filter(
        student_id=student_id,
        institution_id=institution_id,
        completed=True,
        completed_at__isnull=False,
    ).values_list("due_date", "completed_at"):
        completed_day = _to_date(completed_at)
        if completed_day is not None and completed_day <= due_date:
            total += 1
    return total


def _late_tasks(student_id: int, institution_id: int, reference: date) -> int:
    # Tarefas não concluídas e vencidas + concluídas após vencimento
    overdue_incomplete = StudyTask.objects.filter(
        student_id=student_id,
        institution_id=institution_id,
        completed=False,
        due_date__lt=reference,
    ).count()

    overdue_completed = 0
    for due_date, completed_at in StudyTask.objects.filter(
        student_id=student_id,
        institution_id=institution_id,
        completed=True,
        completed_at__isnull=False,
        due_date__lt=reference,
    ).values_list("due_date", "completed_at"):
        if _to_date(completed_at) and completed_at.date() > due_date:
            overdue_completed += 1

    return int(overdue_incomplete + overdue_completed)


def _emotional_count(
    student_id: int,
    institution_id: int,
    reference: date,
    days: int,
    min_motivation: int | None = None,
    max_motivation: int | None = None,
    min_stress: int | None = None,
) -> int:
    start, end = _window_date_bounds(reference, days)
    qs = EmotionalCheckin.objects.filter(
        student_id=student_id,
        institution_id=institution_id,
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    if min_motivation is not None:
        qs = qs.filter(motivation_level__gte=min_motivation)
    if max_motivation is not None:
        qs = qs.filter(motivation_level__lte=max_motivation)
    if min_stress is not None:
        qs = qs.filter(stress_level__gte=min_stress)
    return int(qs.count())


def _last_activity_gap_days(student, institution_id: int, reference: date) -> int:
    latest_session = StudySession.objects.filter(
        student=student,
        institution_id=institution_id,
    ).aggregate(last_session=Max("created_at"))["last_session"]

    latest_completed_task = StudyTask.objects.filter(
        student=student,
        institution_id=institution_id,
        completed=True,
        completed_at__isnull=False,
    ).aggregate(last_task=Max("completed_at"))["last_task"]

    latest_checkin = EmotionalCheckin.objects.filter(
        student=student,
        institution_id=institution_id,
    ).aggregate(last_checkin=Max("created_at"))["last_checkin"]

    candidates = []
    if student.last_login is not None:
        candidates.append(_to_date(student.last_login))
    candidates.append(_to_date(latest_session))
    candidates.append(_to_date(latest_completed_task))
    candidates.append(_to_date(latest_checkin))
    candidates = [d for d in candidates if d is not None]
    if not candidates:
        return 999
    return (reference - max(candidates)).days


def calculate_student_score(student, institution_id: int, at=None) -> int:
    """
    Cálculo determinístico e reexecutável.
    O modelo usa dados comportamentais e não depende de notas escolares.
    """
    if student is None or institution_id is None:
        raise ValueError("student e institution_id são obrigatórios")

    reference = timezone.localtime(at or timezone.now()).date()
    student_id = student.id

    base = 500
    bonus = 0
    penalty = 0

    # login no sistema no dia
    if student.last_login and _to_date(student.last_login) == reference:
        bonus += 5

    # sessão de estudo no dia
    if StudySession.objects.filter(
        student_id=student_id,
        institution_id=institution_id,
        created_at__date=reference,
    ).exists():
        bonus += 10

    # 4+ sessões na semana
    if _sessions_in_window(student_id, institution_id, reference, days=7) >= 4:
        bonus += 30

    # tarefas concluídas no prazo
    bonus += min(_completed_tasks_on_time(student_id, institution_id) * 20, 200)

    # streak de estudo
    streak = _max_streak(_sessions_days_in_window(student_id, institution_id, reference, days=30))
    if streak >= 3:
        bonus += 20
    if streak >= 7:
        bonus += 50

    # 30h acumuladas (em minutos)
    if _minutes_studied_in_window(student_id, institution_id, reference, days=30) >= 30 * 60:
        bonus += 80

    # check-in emocional com boa motivação
    if _emotional_count(student_id, institution_id, reference, days=14, min_motivation=8) > 0:
        bonus += 5

    inactivity_days = _last_activity_gap_days(student, institution_id, reference)
    if inactivity_days >= 14:
        penalty += 150
    elif inactivity_days >= 7:
        penalty += 100
    elif inactivity_days >= 3:
        penalty += 40

    # tarefa atrasada
    penalty += _late_tasks(student_id, institution_id, reference) * 30

    # baixa motivação repetida
    if _emotional_count(student_id, institution_id, reference, days=14, max_motivation=3) >= 3:
        penalty += 20

    # alto estresse repetido
    if _emotional_count(student_id, institution_id, reference, days=14, min_stress=8) >= 3:
        penalty += 10

    # muitos dias sem sessão de estudo na semana
    if _sessions_in_window(student_id, institution_id, reference, days=7) == 0:
        penalty += 30

    return clamp_score(base + bonus - penalty)


def calculate_and_persist_score(student, institution_id: int, at=None) -> AcademicDisciplineScore:
    """
    Recomendado para uso periódico (ex.: tarefa CRON).
    Cada execução persiste um snapshot novo.
    """
    if at is None:
        at = timezone.now()
    value = calculate_student_score(student, institution_id=institution_id, at=at)
    return AcademicDisciplineScore.objects.create(
        student=student,
        institution_id=institution_id,
        score_value=value,
        classification=classify_score(value),
        calculated_at=at,
    )


def calculate_score_payload(student, institution_id: int, at=None) -> dict:
    value = calculate_student_score(student, institution_id=institution_id, at=at)
    return {
        "score_value": value,
        "classification": classify_score(value),
        "calculated_at": at or timezone.now(),
    }


def latest_score(student, institution_id: int):
    return AcademicDisciplineScore.objects.filter(
        student=student,
        institution_id=institution_id,
    ).order_by("-calculated_at").first()
