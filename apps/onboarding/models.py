from django.conf import settings
from django.db import models


class UserSetupProgress(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="setup_progress")
    has_profile = models.BooleanField(default=False)
    has_active_semester = models.BooleanField(default=False)
    has_at_least_one_course = models.BooleanField(default=False)
    has_at_least_one_assessment = models.BooleanField(default=False)
    has_reminder_rule = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email
