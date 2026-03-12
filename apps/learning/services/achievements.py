from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Sum
from django.utils import timezone

from learning.models import Achievement, AcademicDisciplineScore, StudySession, StudyTask
from learning.services.discipline_score import calculate_student_score


def _has_achievement(student_id: int, institution_id: int, achievement_type: str) -> bool:
    return Achievement.objects.filter(
        student_id=student_id,
        institution_id=institution_id,
        achievement_type=achievement_type,
    ).exists()


def _mark(student, institution_id: int, achievement_type: str, title: str, description: str, when: datetime | None = None):
    if when is None:
        when = timezone.now()
    return Achievement.objects.get_or_create(
        student=student,
        institution_id=institution_id,
        achievement_type=achievement_type,
        defaults={
            "title": title,
            "description": description,
            "unlocked_at": when,
        },
    )


def evaluate_consistency_7_days(student, institution_id: int, when=None):
    if _has_achievement(student.id, institution_id, Achievement.ACHIEVEMENT_CONSISTENCY_7_DAYS):
        return
    if when is None:
        when = timezone.now()
    start = (timezone.localtime(when).date() - timedelta(days=6))
    sessions = StudySession.objects.filter(
        student=student,
        institution_id=institution_id,
        created_at__date__gte=start,
        created_at__date__lte=timezone.localtime(when).date(),
    ).values_list("created_at__date", flat=True)
    if len(set(sessions)) >= 7:
        _mark(
            student,
            institution_id,
            Achievement.ACHIEVEMENT_CONSISTENCY_7_DAYS,
            "Semana completa",
            "Você manteve 7 dias seguidos com atividade de estudo.",
            when=when,
        )


def evaluate_tasks_completed(student, institution_id: int, when=None):
    if _has_achievement(student.id, institution_id, Achievement.ACHIEVEMENT_TASKS_10):
        return
    if StudyTask.objects.filter(
        student=student,
        institution_id=institution_id,
        completed=True,
    ).count() >= 10:
        _mark(
            student,
            institution_id,
            Achievement.ACHIEVEMENT_TASKS_10,
            "10 tarefas concluídas",
            "Você já concluiu 10 tarefas de estudo.",
            when=when,
        )


def evaluate_study_30h(student, institution_id: int, when=None):
    if _has_achievement(student.id, institution_id, Achievement.ACHIEVEMENT_STUDY_30H):
        return
    if when is None:
        when = timezone.now()
    end = timezone.localtime(when).date()
    start = end - timedelta(days=29)
    total = (
        StudySession.objects.filter(
            student=student,
            institution_id=institution_id,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).aggregate(total_minutes=Sum("duration_minutes"))["total_minutes"]
        or 0
    )
    if total >= 30 * 60:
        _mark(
            student,
            institution_id,
            Achievement.ACHIEVEMENT_STUDY_30H,
            "30 horas estudadas",
            "Você acumulou 30 horas de estudo.",
            when=when,
        )


def evaluate_score_800(student, institution_id: int, when=None):
    if _has_achievement(student.id, institution_id, Achievement.ACHIEVEMENT_SCORE_800):
        return
    latest = AcademicDisciplineScore.objects.filter(
        student=student,
        institution_id=institution_id,
    ).order_by("-calculated_at").first()
    if latest and latest.score_value >= 800:
        _mark(
            student,
            institution_id,
            Achievement.ACHIEVEMENT_SCORE_800,
            "Mestre da consistência",
            "Seu score ultrapassou 800.",
        )
    elif when is not None:
        score = calculate_student_score(student, institution_id=institution_id, at=when)
        if score >= 800:
            _mark(
                student,
                institution_id,
                Achievement.ACHIEVEMENT_SCORE_800,
                "Mestre da consistência",
                "Seu score ultrapassou 800.",
                when=when,
            )


def run_gamification(student, institution_id: int, when=None):
    evaluate_consistency_7_days(student, institution_id, when=when)
    evaluate_tasks_completed(student, institution_id, when=when)
    evaluate_study_30h(student, institution_id, when=when)
    evaluate_score_800(student, institution_id, when=when)
    return Achievement.objects.filter(student=student, institution_id=institution_id).order_by("-unlocked_at")
