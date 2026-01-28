from rest_framework import serializers

from planner.models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "due_date",
            "stress_level",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
