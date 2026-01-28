from django.db import transaction

from billing.models import Plan
from utils.constants import (
    FEATURE_AGENDA_BASIC,
    FEATURE_COACH_ADVANCED,
    FEATURE_CONTENT_FULL,
    FEATURE_CONTENT_LIMITED,
    FEATURE_DASHBOARD_BASIC,
    FEATURE_EMAIL_NOTIFICATIONS,
    FEATURE_IN_APP_REMINDERS,
    FEATURE_MOOD_BASIC,
    FEATURE_PLANNER_BASIC,
    FEATURE_POMODORO_BASIC,
    FEATURE_REPORTS_ADVANCED,
    FEATURE_SEMESTER_SUMMARY,
    PLAN_LITE,
    PLAN_PRO,
)


def seed_plans(sender, **kwargs):
    with transaction.atomic():
        Plan.objects.get_or_create(
            code=PLAN_LITE,
            defaults={
                "name": "Lite",
                "description": "Plano basico para organizacao e bem-estar.",
                "features": [
                    FEATURE_MOOD_BASIC,
                    FEATURE_POMODORO_BASIC,
                    FEATURE_PLANNER_BASIC,
                    FEATURE_AGENDA_BASIC,
                    FEATURE_IN_APP_REMINDERS,
                    FEATURE_DASHBOARD_BASIC,
                    FEATURE_CONTENT_LIMITED,
                ],
                "is_active": True,
            },
        )
        Plan.objects.get_or_create(
            code=PLAN_PRO,
            defaults={
                "name": "Pro",
                "description": "Plano completo com notificacoes e relatorios.",
                "features": [
                    FEATURE_MOOD_BASIC,
                    FEATURE_POMODORO_BASIC,
                    FEATURE_PLANNER_BASIC,
                    FEATURE_AGENDA_BASIC,
                    FEATURE_IN_APP_REMINDERS,
                    FEATURE_DASHBOARD_BASIC,
                    FEATURE_CONTENT_LIMITED,
                    FEATURE_EMAIL_NOTIFICATIONS,
                    FEATURE_REPORTS_ADVANCED,
                    FEATURE_SEMESTER_SUMMARY,
                    FEATURE_COACH_ADVANCED,
                    FEATURE_CONTENT_FULL,
                ],
                "is_active": True,
            },
        )
