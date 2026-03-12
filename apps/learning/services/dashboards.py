from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from accounts.models import ParentProfile, StudentProfile, User
from accounts.permissions import can_view_rankings
from accounts.services.student_profiles import active_institution_students
from learning.models import AcademicDisciplineScore, Achievement, EmotionalCheckin, StudySession, StudyTask
from learning.services.discipline_score import calculate_score_payload, classify_score, latest_score
from utils.localization import get_user_language, localized_text


def _today():
    return timezone.localdate()


def _study_days(student_id: int, institution_id: int, days: int) -> list:
    start = _today() - timedelta(days=days - 1)
    return list(
        StudySession.objects.filter(
            student_id=student_id,
            institution_id=institution_id,
            created_at__date__gte=start,
            created_at__date__lte=_today(),
        ).values_list("created_at__date", flat=True)
    )


def _max_streak(days: list) -> int:
    ordered = sorted(set(days))
    if not ordered:
        return 0
    longest = 1
    current = 1
    for index in range(1, len(ordered)):
        if (ordered[index] - ordered[index - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _latest_score_or_calculated(student, institution_id: int) -> dict:
    score = latest_score(student, institution_id)
    if score is not None:
        return {
            "score_value": score.score_value,
            "classification": score.classification,
            "calculated_at": score.calculated_at,
        }
    return calculate_score_payload(student, institution_id)


def _student_alerts(student, institution_id: int, language_code: str) -> list[str]:
    alerts = []
    overdue_tasks = StudyTask.objects.filter(
        student=student,
        institution_id=institution_id,
        completed=False,
        due_date__lt=_today(),
    ).count()
    weekly_sessions = StudySession.objects.filter(
        student=student,
        institution_id=institution_id,
        created_at__date__gte=_today() - timedelta(days=6),
    ).count()
    stress_avg = (
        EmotionalCheckin.objects.filter(
            student=student,
            institution_id=institution_id,
            created_at__date__gte=_today() - timedelta(days=13),
        ).aggregate(avg=Avg("stress_level"))["avg"]
        or 0
    )
    if overdue_tasks:
        alerts.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Você tem tarefas atrasadas. Vale reorganizar a semana e atacar primeiro o que já venceu.",
                    "en": "You have overdue study tasks. Reorganize the week and handle the overdue items first.",
                    "es": "Tienes tareas atrasadas. Reorganiza la semana y resuelve primero lo vencido.",
                },
            )
        )
    if weekly_sessions <= 1:
        alerts.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Sua consistência de estudo está baixa nesta semana.",
                    "en": "Your study consistency is low this week.",
                    "es": "Tu consistencia de estudio está baja esta semana.",
                },
            )
        )
    if stress_avg >= 8:
        alerts.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Seu nível de pressão parece alto. Tente reduzir a carga em blocos menores.",
                    "en": "Your pressure level seems high. Try splitting the workload into smaller blocks.",
                    "es": "Tu nivel de presión parece alto. Intenta dividir la carga en bloques más pequeños.",
                },
            )
        )
    return alerts


def _student_recommendations(student, institution_id: int, language_code: str, score_value: int) -> list[str]:
    sessions_7 = StudySession.objects.filter(
        student=student,
        institution_id=institution_id,
        created_at__date__gte=_today() - timedelta(days=6),
    ).count()
    recommendations = []
    if score_value <= 500 or sessions_7 <= 2:
        recommendations.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Comece com sessões de 25 minutos e pausas curtas de 5 minutos para reconstruir o hábito.",
                    "en": "Start with 25-minute sessions and short 5-minute breaks to rebuild the habit.",
                    "es": "Empieza con sesiones de 25 minutos y pausas cortas de 5 minutos para reconstruir el hábito.",
                },
            )
        )
    else:
        recommendations.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Você está indo bem. Aumente gradualmente o desafio e revise conteúdos antigos.",
                    "en": "You are doing well. Increase the challenge gradually and revisit older topics.",
                    "es": "Vas bien. Aumenta gradualmente el desafío y revisa contenidos anteriores.",
                },
            )
        )
    recommendations.append(
        localized_text(
            language_code,
            {
                "pt-BR": "Refaça os exercícios que você errou, entenda o erro e só depois resolva novamente sem consultar.",
                "en": "Redo the exercises you missed, understand the mistake, then solve them again without checking.",
                "es": "Rehaz los ejercicios que fallaste, entiende el error y luego resuélvelos de nuevo sin consultar.",
            },
        )
    )
    return recommendations


def student_dashboard(user, institution_id: int | None = None) -> dict:
    institution_id = institution_id or user.institution_id
    language_code = get_user_language(user)
    current_score = _latest_score_or_calculated(user, institution_id)
    task_scope = StudyTask.objects.filter(student=user, institution_id=institution_id)
    pending_tasks = task_scope.filter(completed=False).order_by("due_date")
    completed_tasks = task_scope.filter(completed=True).order_by("-completed_at")
    study_days = _study_days(user.id, institution_id, 30)

    return {
        "score_current": current_score,
        "score_evolution": list(
            AcademicDisciplineScore.objects.filter(student=user, institution_id=institution_id)
            .order_by("-calculated_at")
            .values("score_value", "classification", "calculated_at")[:12]
        )[::-1],
        "tasks_pending": list(pending_tasks.values("id", "title", "due_date")[:10]),
        "tasks_completed": list(completed_tasks.values("id", "title", "completed_at")[:10]),
        "study_consistency": {
            "sessions_last_7_days": StudySession.objects.filter(
                student=user,
                institution_id=institution_id,
                created_at__date__gte=_today() - timedelta(days=6),
            ).count(),
            "study_days_last_30_days": len(set(study_days)),
            "current_streak_days": _max_streak(study_days),
        },
        "achievements": list(
            Achievement.objects.filter(student=user, institution_id=institution_id)
            .order_by("-unlocked_at")
            .values("achievement_type", "title", "description", "unlocked_at")
        ),
        "friendly_alerts": _student_alerts(user, institution_id, language_code),
        "recommendations": _student_recommendations(
            user,
            institution_id,
            language_code,
            current_score["score_value"],
        ),
    }


def parent_dashboard(user, institution_id: int | None = None) -> dict:
    institution_id = institution_id or user.institution_id
    children_links = ParentProfile.objects.filter(user=user, institution_id=institution_id).select_related("student", "student__user")
    children = []
    for link in children_links:
        child_dashboard = student_dashboard(link.student.user, institution_id=link.student.institution_id)
        children.append(
            {
                "student_id": link.student.id,
                "student_name": link.student.user.name,
                "relationship_type": link.relationship_type,
                "score_current": child_dashboard["score_current"],
                "study_consistency": child_dashboard["study_consistency"],
                "tasks_completed": child_dashboard["tasks_completed"][:5],
                "friendly_alerts": child_dashboard["friendly_alerts"],
            }
        )
    return {"children": children}


def _score_distribution(score_values: list[int]) -> list[dict]:
    bands = defaultdict(int)
    for value in score_values:
        bands[classify_score(value)] += 1
    return [{"classification": key, "total": total} for key, total in bands.items()]


def _pedagogical_insights(language_code: str, metrics: dict) -> list[str]:
    insights = []
    if metrics["at_risk_total"] > 0:
        insights.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Há alunos com baixa consistência de estudo nesta turma.",
                    "en": "There are students with low study consistency in this group.",
                    "es": "Hay estudiantes con baja consistencia de estudio en este grupo.",
                },
            )
        )
    if metrics["overdue_total"] > 0:
        insights.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Alguns alunos apresentam risco de procrastinação.",
                    "en": "Some students show signs of procrastination risk.",
                    "es": "Algunos estudiantes presentan riesgo de procrastinación.",
                },
            )
        )
    if metrics["high_stress_total"] > 0:
        insights.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Considere estratégias de acompanhamento mais próximo.",
                    "en": "Consider closer follow-up strategies.",
                    "es": "Considera estrategias de acompañamiento más cercano.",
                },
            )
        )
        insights.append(
            localized_text(
                language_code,
                {
                    "pt-BR": "Alguns alunos podem se beneficiar de apoio individualizado.",
                    "en": "Some students may benefit from individualized support.",
                    "es": "Algunos estudiantes pueden beneficiarse de apoyo individualizado.",
                },
            )
        )
    return insights


def teacher_dashboard(
    user,
    institution_id: int | None = None,
    class_group: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    institution_id = institution_id or user.institution_id
    language_code = get_user_language(user)
    profiles = active_institution_students(institution_id)
    if class_group:
        profiles = profiles.filter(class_group=class_group)

    rows = []
    for profile in profiles:
        score_data = _latest_score_or_calculated(profile.user, institution_id)
        overdue = StudyTask.objects.filter(
            student=profile.user,
            institution_id=institution_id,
            completed=False,
            due_date__lt=_today(),
        ).count()
        weekly_sessions = StudySession.objects.filter(
            student=profile.user,
            institution_id=institution_id,
            created_at__date__gte=_today() - timedelta(days=6),
        ).count()
        high_stress = EmotionalCheckin.objects.filter(
            student=profile.user,
            institution_id=institution_id,
            created_at__date__gte=_today() - timedelta(days=13),
            stress_level__gte=8,
        ).count()
        rows.append(
            {
                "student_id": profile.user_id,
                "student_name": profile.user.name,
                "class_group": profile.class_group,
                "score_value": score_data["score_value"],
                "classification": score_data["classification"],
                "weekly_sessions": weekly_sessions,
                "overdue_tasks": overdue,
                "high_stress_events": high_stress,
            }
        )

    rows.sort(key=lambda item: item["score_value"], reverse=True)
    if search:
        search_term = search.strip().lower()
        rows = [row for row in rows if search_term in (row["student_name"] or "").lower()]
    score_values = [row["score_value"] for row in rows]
    metrics = {
        "at_risk_total": len([row for row in rows if row["score_value"] <= 500 or row["weekly_sessions"] <= 1]),
        "overdue_total": len([row for row in rows if row["overdue_tasks"] > 0]),
        "high_stress_total": len([row for row in rows if row["high_stress_events"] >= 2]),
    }
    total_items = len(rows)
    total_pages = max(1, (total_items + page_size - 1) // page_size) if page_size else 1
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    paginated_rows = rows[start:end]

    return {
        "class_average": round(sum(score_values) / len(score_values), 2) if score_values else 0,
        "students_at_risk": [row for row in rows if row["score_value"] <= 500 or row["weekly_sessions"] <= 1],
        "students_low_consistency": [row for row in rows if row["weekly_sessions"] <= 1],
        "students_good_discipline": [row for row in rows if row["score_value"] >= 701],
        "pedagogical_insights": _pedagogical_insights(language_code, metrics),
        "ranking": paginated_rows if can_view_rankings(user) else [],
        "ranking_pagination": {
            "page": current_page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_previous": current_page > 1,
        },
        "ranking_filters": {
            "class_group": class_group or "",
            "search": search or "",
        },
        "distribution": _score_distribution(score_values),
    }


def institution_dashboard(user, institution_id: int | None = None) -> dict:
    institution_id = institution_id or user.institution_id
    language_code = get_user_language(user)
    profiles = list(active_institution_students(institution_id))
    rows = []
    by_class = defaultdict(list)

    for profile in profiles:
        score_data = _latest_score_or_calculated(profile.user, institution_id)
        by_class[profile.class_group or "Sem turma"].append(score_data["score_value"])
        rows.append(
            {
                "student_id": profile.user_id,
                "student_name": profile.user.name,
                "class_group": profile.class_group or "Sem turma",
                "score_value": score_data["score_value"],
                "classification": score_data["classification"],
            }
        )

    rows.sort(key=lambda item: item["score_value"], reverse=True)
    class_rankings = []
    for class_group, values in by_class.items():
        class_rankings.append(
            {
                "class_group": class_group,
                "average_score": round(sum(values) / len(values), 2) if values else 0,
                "students_total": len(values),
            }
        )
    class_rankings.sort(key=lambda item: item["average_score"], reverse=True)

    score_values = [row["score_value"] for row in rows]
    metrics = {
        "at_risk_total": len([row for row in rows if row["score_value"] <= 500]),
        "overdue_total": StudyTask.objects.filter(
            institution_id=institution_id,
            completed=False,
            due_date__lt=_today(),
        ).count(),
        "high_stress_total": EmotionalCheckin.objects.filter(
            institution_id=institution_id,
            created_at__date__gte=_today() - timedelta(days=13),
            stress_level__gte=8,
        ).count(),
    }

    return {
        "institution_average": round(sum(score_values) / len(score_values), 2) if score_values else 0,
        "average_by_class": class_rankings,
        "students_at_risk": [row for row in rows if row["score_value"] <= 500],
        "class_ranking": class_rankings,
        "discipline_distribution": _score_distribution(score_values),
        "top_students": rows[:10] if can_view_rankings(user) else [],
        "pedagogical_insights": _pedagogical_insights(language_code, metrics),
    }
