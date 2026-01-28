from django.conf import settings
from django.db import models

from utils.constants import CHANNEL_CHOICES, NOTIFICATION_STATUS_CHOICES, NOTIF_PENDING


class NotificationQueue(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS_CHOICES, default=NOTIF_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.channel}"
