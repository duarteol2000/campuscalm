from django.conf import settings
from django.db import models

from utils.constants import (
    CHANNEL_CHOICES,
    NOTIFICATION_ACTION_CHOICES,
    NOTIFICATION_STATUS_CHOICES,
    ACTION_NONE,
    NOTIF_PENDING,
)


# Bloco: Fila de notificacoes
class NotificationQueue(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS_CHOICES, default=NOTIF_PENDING)
    action_taken = models.CharField(max_length=20, choices=NOTIFICATION_ACTION_CHOICES, default=ACTION_NONE)
    provider = models.CharField(max_length=50, blank=True)
    provider_message_id = models.CharField(max_length=200, blank=True)
    last_error = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    to_phone = models.CharField(max_length=30, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.channel}"


# Bloco: Mensagens recebidas do WhatsApp
class IncomingMessage(models.Model):
    phone_from = models.CharField(max_length=30)
    text = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)
    raw_payload = models.JSONField()
    parsed_action = models.CharField(max_length=20, choices=NOTIFICATION_ACTION_CHOICES, default=ACTION_NONE)
    matched_notification = models.ForeignKey(
        NotificationQueue, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_messages"
    )

    def __str__(self):
        return f"{self.phone_from} - {self.received_at:%Y-%m-%d %H:%M}"


# Bloco: Notificacoes in-app (sino da topbar)
class InAppNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    target_url = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.title}"
