from rest_framework import serializers

from notifications.models import NotificationQueue


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
