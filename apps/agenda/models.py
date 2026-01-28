from django.conf import settings
from django.db import models

from planner.models import Task
from utils.constants import EVENT_TYPE_CHOICES, REMINDER_TARGET_CHOICES


class CalendarEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    related_task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ReminderRule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminder_rules")
    target_type = models.CharField(max_length=10, choices=REMINDER_TARGET_CHOICES)
    remind_before_minutes = models.PositiveIntegerField()
    channels = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} - {self.target_type}"
