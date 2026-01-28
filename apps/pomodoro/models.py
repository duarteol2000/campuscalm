from django.conf import settings
from django.db import models
from django.utils import timezone

from utils.constants import POMODORO_STATUS_CHOICES, POMODORO_STOPPED


class PomodoroSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pomodoro_sessions")
    focus_minutes = models.PositiveIntegerField(default=25)
    break_minutes = models.PositiveIntegerField(default=5)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=POMODORO_STATUS_CHOICES, default=POMODORO_STOPPED)

    def __str__(self):
        return f"{self.user.email} - {self.status}"
