from typing import List, Tuple

from django.utils.translation import gettext_lazy as _

from utils.constants import (
    STEP_1_PROFILE,
    STEP_2_SEMESTER,
    STEP_3_COURSES,
    STEP_4_ASSESSMENTS,
    STEP_5_REMINDERS,
    STEP_6_DASHBOARD,
)

STEPS = [
    (STEP_1_PROFILE, "has_profile", _("Complete seu perfil para continuar.")),
    (STEP_2_SEMESTER, "has_active_semester", _("Crie um semestre ativo.")),
    (STEP_3_COURSES, "has_at_least_one_course", _("Cadastre ao menos uma disciplina.")),
    (STEP_4_ASSESSMENTS, "has_at_least_one_assessment", _("Cadastre ao menos uma avaliacao.")),
    (STEP_5_REMINDERS, "has_reminder_rule", _("Configure pelo menos uma regra de lembrete.")),
    (STEP_6_DASHBOARD, None, _("Tudo pronto para seu dashboard.")),
]


def get_or_create_progress(user):
    from onboarding.models import UserSetupProgress

    progress, _ = UserSetupProgress.objects.get_or_create(user=user)
    return progress


def compute_status(progress) -> Tuple[str, List[str], List[str]]:
    missing_steps = []
    required_actions = []
    for step, field, message in STEPS:
        if field is None:
            continue
        if not getattr(progress, field):
            missing_steps.append(step)
            required_actions.append(message)
    current_step = missing_steps[0] if missing_steps else STEP_6_DASHBOARD
    return current_step, missing_steps, required_actions


def gate_course_progress(course) -> Tuple[bool, str]:
    if not course.assessments.exists():
        return False, "Cadastre ao menos uma avaliacao antes de ver o progresso."
    return True, ""


def gate_finish_semester(semester) -> Tuple[bool, str]:
    if not semester.courses.exists():
        return False, "Nao e possivel finalizar um semestre sem disciplinas."
    return True, ""


def gate_generate_reminders(user) -> Tuple[bool, str]:
    from agenda.models import ReminderRule

    if not ReminderRule.objects.filter(user=user, is_active=True).exists():
        return False, "Configure uma regra de lembrete antes de gerar notificacoes."
    return True, ""
