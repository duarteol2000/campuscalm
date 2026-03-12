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
    PLAN_ENTERPRISE,
    PLAN_LITE,
    PLAN_PILOT,
    PLAN_PRO,
    PLAN_SCHOOL,
    PLAN_STARTER,
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
        Plan.objects.get_or_create(
            code=PLAN_PILOT,
            defaults={
                "name": "Piloto",
                "description": "Plano piloto institucional para validacao de longo prazo.",
                "features": Plan.default_pro_features(),
                "price": 0,
                "max_students": 300,
                "is_active": True,
            },
        )
        Plan.objects.get_or_create(
            code=PLAN_STARTER,
            defaults={
                "name": "Starter",
                "description": "Plano institucional de entrada.",
                "features": Plan.default_lite_features(),
                "price": 199,
                "max_students": 300,
                "is_active": True,
            },
        )
        Plan.objects.get_or_create(
            code=PLAN_SCHOOL,
            defaults={
                "name": "School",
                "description": "Plano institucional para operacao escolar completa.",
                "features": Plan.default_pro_features(),
                "price": 799,
                "max_students": 2000,
                "is_active": True,
            },
        )
        Plan.objects.get_or_create(
            code=PLAN_ENTERPRISE,
            defaults={
                "name": "Enterprise",
                "description": "Plano corporativo para redes e instituicoes de grande porte.",
                "features": Plan.default_pro_features(),
                "price": 1999,
                "max_students": 0,
                "is_active": True,
            },
        )
