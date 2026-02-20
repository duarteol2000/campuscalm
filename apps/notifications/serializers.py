from rest_framework import serializers

from notifications.models import InAppNotification, NotificationQueue


class NotificationQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationQueue
        fields = (
            "id",
            "channel",
            "title",
            "message",
            "scheduled_for",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ("id", "title", "body", "target_url", "is_read", "created_at")
        read_only_fields = ("id", "created_at")
