from rest_framework import serializers

from mood.models import MoodEntry


class MoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = ("id", "mood", "notes", "tags", "created_at")
        read_only_fields = ("id", "created_at")


class MoodWeeklySummarySerializer(serializers.Serializer):
    summary = serializers.DictField(child=serializers.IntegerField())
