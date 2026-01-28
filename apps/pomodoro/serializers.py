from rest_framework import serializers

from pomodoro.models import PomodoroSession


class PomodoroSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PomodoroSession
        fields = (
            "id",
            "focus_minutes",
            "break_minutes",
            "started_at",
            "ended_at",
            "status",
        )
        read_only_fields = ("id", "started_at", "ended_at", "status")
