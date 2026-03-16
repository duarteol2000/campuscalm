from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, OuterRef, Q, Subquery
from django.db.models.functions import TruncWeek
from django.utils import timezone

from accounts.models import ClassGroup, ParentProfile, StudentProfile, TeacherAssignment, User
from accounts.permissions import can_access_class_group
from accounts.services.student_profiles import active_institution_students
from learning.models import AcademicDisciplineScore, Achievement, EmotionalCheckin, StudySession, StudyTask
from learning.services.discipline_score import calculate_score_payload, classify_score, latest_score
from utils.localization import get_user_language, localized_text


def _today():
    return timezone.localdate()


def _current_week_start():
    today = _today()
    return today - timedelta(days=today.weekday())


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


def _assigned_class_ids_and_names(user, institution_id: int) -> tuple[list[int], list[str]]:
    assignments = TeacherAssignment.objects.filter(
        teacher=user,
        institution_id=institution_id,
    ).select_related("class_group")
    class_ids = []
    class_names = []
    for assignment in assignments:
        class_ids.append(assignment.class_group_id)
        class_names.append(assignment.class_group.name)
    return class_ids, class_names


def _scoped_profiles(user, institution_id: int):
    profiles = active_institution_students(institution_id).select_related("user", "institution", "class_group_ref")
    if getattr(user, "is_superuser", False) or user.role in {User.ROLE_COORDINATOR, User.ROLE_INSTITUTION_ADMIN}:
        return profiles
    if user.role != User.ROLE_TEACHER:
        return profiles.none()

    assigned_ids, assigned_names = _assigned_class_ids_and_names(user, institution_id)
    if not assigned_ids and not assigned_names:
        return profiles.none()
    return profiles.filter(
        Q(class_group_ref_id__in=assigned_ids)
        | (Q(class_group_ref__isnull=True) & Q(class_group__in=assigned_names))
    )


def _filter_profiles_by_class_obj(profiles, class_group_obj: ClassGroup):
    return profiles.filter(
        Q(class_group_ref_id=class_group_obj.id)
        | (
            Q(class_group_ref__isnull=True)
            & Q(class_group=class_group_obj.name)
            & Q(grade_level=class_group_obj.grade_level)
        )
    )


def _filter_profiles_by_class_name(profiles, class_group: str):
    return profiles.filter(
        Q(class_group_ref__name=class_group)
        | (Q(class_group_ref__isnull=True) & Q(class_group=class_group))
    )


def _annotated_profiles_for_scores(profiles, institution_id: int):
    latest_score_scope = AcademicDisciplineScore.objects.filter(
        student_id=OuterRef("user_id"),
        institution_id=institution_id,
    ).order_by("-calculated_at")
    return profiles.annotate(
        latest_score_value=Subquery(latest_score_scope.values("score_value")[:1]),
        latest_score_classification=Subquery(latest_score_scope.values("classification")[:1]),
        latest_score_calculated_at=Subquery(latest_score_scope.values("calculated_at")[:1]),
    )


def _support_metric_maps(user_ids: list[int], institution_id: int) -> tuple[dict, dict, dict]:
    weekly_map = dict(
        StudySession.objects.filter(
            student_id__in=user_ids,
            institution_id=institution_id,
            created_at__date__gte=_today() - timedelta(days=6),
        )
        .values("student_id")
        .annotate(total=Count("id"))
        .values_list("student_id", "total")
    )
    overdue_map = dict(
        StudyTask.objects.filter(
            student_id__in=user_ids,
            institution_id=institution_id,
            completed=False,
            due_date__lt=_today(),
        )
        .values("student_id")
        .annotate(total=Count("id"))
        .values_list("student_id", "total")
    )
    stress_map = dict(
        EmotionalCheckin.objects.filter(
            student_id__in=user_ids,
            institution_id=institution_id,
            created_at__date__gte=_today() - timedelta(days=13),
            stress_level__gte=8,
        )
        .values("student_id")
        .annotate(total=Count("id"))
        .values_list("student_id", "total")
    )
    return weekly_map, overdue_map, stress_map


def _build_student_rows(profiles, institution_id: int, search: str | None = None) -> list[dict]:
    rows = []
    profiles = _annotated_profiles_for_scores(profiles, institution_id)
    user_ids = list(profiles.values_list("user_id", flat=True))
    weekly_map, overdue_map, stress_map = _support_metric_maps(user_ids, institution_id)

    search_term = (search or "").strip().lower()
    for profile in profiles:
        if profile.latest_score_value is None:
            score_data = calculate_score_payload(profile.user, institution_id)
        else:
            score_data = {
                "score_value": profile.latest_score_value,
                "classification": profile.latest_score_classification,
                "calculated_at": profile.latest_score_calculated_at,
            }

        if search_term and search_term not in (profile.user.name or "").lower():
            continue

        rows.append(
            {
                "student_id": profile.user_id,
                "student_name": profile.user.name,
                "class_id": profile.class_group_ref_id,
                "class_group": profile.class_group_ref.name if profile.class_group_ref_id else profile.class_group,
                "grade_level": profile.class_group_ref.grade_level if profile.class_group_ref_id else profile.grade_level,
                "score_value": score_data["score_value"],
                "classification": score_data["classification"],
                "weekly_sessions": weekly_map.get(profile.user_id, 0),
                "overdue_tasks": overdue_map.get(profile.user_id, 0),
                "high_stress_events": stress_map.get(profile.user_id, 0),
            }
        )
    rows.sort(key=lambda item: item["score_value"], reverse=True)
    return rows


def _class_summary_from_rows(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(lambda: {"score_total": 0, "student_count": 0})
    labels = {}
    for row in rows:
        key = (row["class_id"], row["class_group"], row["grade_level"])
        grouped[key]["score_total"] += row["score_value"]
        grouped[key]["student_count"] += 1
        labels[key] = {
            "class_id": row["class_id"],
            "class_name": row["class_group"],
            "grade_level": row["grade_level"],
        }

    summaries = []
    for key, totals in grouped.items():
        label_data = labels[key]
        summaries.append(
            {
                "class_id": label_data["class_id"],
                "class_name": label_data["class_name"],
                "grade_level": label_data["grade_level"],
                "student_count": totals["student_count"],
                "avg_score": round(totals["score_total"] / totals["student_count"], 2) if totals["student_count"] else 0,
            }
        )
    summaries.sort(key=lambda item: item["avg_score"], reverse=True)
    return summaries


def _class_average_ranking(institution_id: int) -> list[dict]:
    profiles = active_institution_students(institution_id).select_related("class_group_ref", "user")
    rows = _build_student_rows(profiles, institution_id)
    return _class_summary_from_rows(rows)


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
        "recommendations": _student_recommendations(user, institution_id, language_code, current_score["score_value"]),
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
    profiles = _scoped_profiles(user, institution_id)
    if class_group:
        profiles = _filter_profiles_by_class_name(profiles, class_group)

    rows = _build_student_rows(profiles, institution_id, search=search)
    class_summaries = _class_summary_from_rows(rows)
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
        "my_classes": class_summaries,
        "average_by_class": class_summaries,
        "class_average": round(sum(score_values) / len(score_values), 2) if score_values else 0,
        "students_at_risk": [row for row in rows if row["score_value"] <= 500][:5],
        "students_low_consistency": [row for row in rows if row["weekly_sessions"] <= 1][:5],
        "students_good_discipline": [row for row in rows if row["score_value"] >= 701][:5],
        "pedagogical_insights": _pedagogical_insights(language_code, metrics),
        "ranking": paginated_rows,
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
    profiles = active_institution_students(institution_id).select_related("user", "class_group_ref")
    rows = _build_student_rows(profiles, institution_id)
    score_values = [row["score_value"] for row in rows]
    class_summaries = _class_summary_from_rows(rows)
    metrics = {
        "at_risk_total": len([row for row in rows if row["score_value"] <= 500]),
        "overdue_total": len([row for row in rows if row["overdue_tasks"] > 0]),
        "high_stress_total": len([row for row in rows if row["high_stress_events"] >= 2]),
    }
    return {
        "institution_average": round(sum(score_values) / len(score_values), 2) if score_values else 0,
        "average_by_class": [
            {
                "class_id": item["class_id"],
                "class_group": item["class_name"],
                "grade_level": item["grade_level"],
                "average_score": item["avg_score"],
                "students_total": item["student_count"],
            }
            for item in class_summaries
        ],
        "students_at_risk": [row for row in rows if row["score_value"] <= 500][:10],
        "class_ranking": [
            {
                "class_id": item["class_id"],
                "class_group": item["class_name"],
                "grade_level": item["grade_level"],
                "average_score": item["avg_score"],
                "students_total": item["student_count"],
            }
            for item in class_summaries
        ],
        "discipline_distribution": _score_distribution(score_values),
        "top_students": rows[:10],
        "pedagogical_insights": _pedagogical_insights(language_code, metrics),
    }


def class_trend_dashboard(user, class_group: ClassGroup) -> dict:
    profiles = _filter_profiles_by_class_obj(_scoped_profiles(user, class_group.institution_id), class_group)
    student_ids = list(profiles.values_list("user_id", flat=True))
    week_start = _current_week_start() - timedelta(weeks=7)
    week_buckets = [week_start + timedelta(weeks=index) for index in range(8)]
    week_labels = [f"W{index + 1}" for index in range(8)]
    week_values = {bucket: 0 for bucket in week_buckets}

    weekly_scores = (
        AcademicDisciplineScore.objects.filter(
            student_id__in=student_ids,
            institution_id=class_group.institution_id,
            calculated_at__date__gte=week_start,
        )
        .annotate(week=TruncWeek("calculated_at"))
        .values("week")
        .annotate(avg_score=Avg("score_value"))
        .order_by("week")
    )

    for entry in weekly_scores:
        week = entry["week"].date() if hasattr(entry["week"], "date") else entry["week"]
        if week in week_values:
            week_values[week] = round(entry["avg_score"], 2)

    return {
        "class_id": class_group.id,
        "class_name": class_group.name,
        "weeks": week_labels,
        "avg_score": [week_values[bucket] for bucket in week_buckets],
    }


def class_heatmap_dashboard(user, class_group: ClassGroup) -> list[dict]:
    profiles = _filter_profiles_by_class_obj(_scoped_profiles(user, class_group.institution_id), class_group)
    rows = _build_student_rows(profiles, class_group.institution_id)

    def score_level(score_value: int) -> str:
        if score_value >= 800:
            return "green"
        if score_value >= 600:
            return "yellow"
        if score_value >= 400:
            return "orange"
        return "red"

    return [
        {
            "student_id": row["student_id"],
            "name": row["student_name"],
            "score": row["score_value"],
            "level": score_level(row["score_value"]),
        }
        for row in rows
    ]


def resolve_accessible_class_group(user, class_id: int):
    class_group = ClassGroup.objects.select_related("institution").filter(id=class_id).first()
    if class_group is None:
        return None
    if not can_access_class_group(user, class_group):
        return None
    return class_group
