from __future__ import annotations

from django.utils import timezone
from typing import List

from django.db.models import QuerySet

from accounts.models import StudentProfile


def active_institution_students(institution_id) -> QuerySet[StudentProfile]:
    """
    Retorna somente alunos ativos para visualização de dashboards institucionais.
    Exclui formados, transferidos, suspensos e contas pessoais.
    """
    return (
        StudentProfile.objects.filter(
            institution_id=institution_id,
            status=StudentProfile.STATUS_ACTIVE,
            account_type=StudentProfile.ACCOUNT_INSTITUTIONAL,
        )
        .select_related("user", "institution")
    )


def historical_students(institution_id) -> QuerySet[StudentProfile]:
    """
    Retorna histórico completo de alunos vinculados à instituição
    (inclui formados e demais estados de inatividade).
    """
    return StudentProfile.objects.filter(institution_id=institution_id).select_related("user", "institution")


def graduate_student(profile: StudentProfile, as_personal_account: bool = False, at=None) -> StudentProfile:
    """
    Marca aluno como formado preservando histórico.
    Se `as_personal_account=True`, converte para conta pessoal imediatamente.
    """
    profile.status = StudentProfile.STATUS_GRADUATED
    if as_personal_account:
        profile.account_type = StudentProfile.ACCOUNT_PERSONAL
    profile.graduated_at = at or timezone.now()
    profile.save(update_fields=["status", "account_type", "graduated_at", "updated_at"])
    return profile


def can_show_in_active_dashboards(student: StudentProfile) -> bool:
    """
    Regra de negócio consolidada para filtros de dashboard:
    apenas status ativo + conta institucional.
    """
    return bool(
        student.is_active_for_institution
    )


def normalize_student_dashboard_ids(institution_id) -> List[int]:
    """
    Retorna lista de IDs para uso em querysets compostos em fases futuras.
    """
    return list(active_institution_students(institution_id).values_list("id", flat=True))
