from django.conf import settings
from django.db import models

from utils.constants import PLAN_CHOICES, PLAN_LITE


class Plan(models.Model):
    code = models.CharField(max_length=10, choices=PLAN_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code}"

    @staticmethod
    def default_lite_features():
        return [
            "MOOD_BASIC",
            "POMODORO_BASIC",
            "PLANNER_BASIC",
            "AGENDA_BASIC",
            "IN_APP_REMINDERS",
            "DASHBOARD_BASIC",
            "CONTENT_LIMITED",
        ]

    @staticmethod
    def default_pro_features():
        return Plan.default_lite_features() + [
            "EMAIL_NOTIFICATIONS",
            "REPORTS_ADVANCED",
            "SEMESTER_SUMMARY",
            "COACH_ADVANCED",
            "CONTENT_FULL",
        ]


class UserSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.code if self.plan else PLAN_LITE}"
