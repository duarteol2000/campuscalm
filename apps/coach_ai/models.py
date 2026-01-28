from django.conf import settings
from django.db import models

from utils.constants import COACH_TRIGGER_CHOICES


class CoachLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coach_logs")
    trigger_type = models.CharField(max_length=30, choices=COACH_TRIGGER_CHOICES)
    suggestion_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.trigger_type}"
