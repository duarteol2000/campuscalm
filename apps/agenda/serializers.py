from rest_framework import serializers

from agenda.models import CalendarEvent, ReminderRule


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "title",
            "event_type",
            "start_at",
            "end_at",
            "related_task",
            "notes",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class ReminderRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderRule
        fields = ("id", "target_type", "remind_before_minutes", "channels", "is_active")
        read_only_fields = ("id",)
