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


class PomodoroStartSerializer(serializers.Serializer):
    focus_minutes = serializers.IntegerField(required=False, min_value=1, default=25)
    break_minutes = serializers.IntegerField(required=False, min_value=1, default=5)


class PomodoroStopSerializer(serializers.Serializer):
    completed = serializers.BooleanField(required=False, default=False)


class PomodoroWeeklySummarySerializer(serializers.Serializer):
    total_sessions = serializers.IntegerField()
    total_focus_minutes = serializers.IntegerField()
