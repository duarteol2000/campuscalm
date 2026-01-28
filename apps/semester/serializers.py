from decimal import Decimal

from rest_framework import serializers

from semester.models import Assessment, Course, Semester, SemesterCheckin
from utils.academic_progress import (
    calculate_course_average,
    calculate_needed_to_pass,
    calculate_progress_percent,
)


class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ("id", "name", "start_date", "end_date", "status")
        read_only_fields = ("id",)


class CourseSerializer(serializers.ModelSerializer):
    current_average = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    needed_to_pass = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "semester",
            "title",
            "teacher",
            "credits",
            "passing_grade",
            "status",
            "final_grade",
            "notes",
            "current_average",
            "progress_percent",
            "needed_to_pass",
        )
        read_only_fields = ("id", "status", "final_grade", "current_average", "progress_percent", "needed_to_pass")

    def get_current_average(self, obj):
        return calculate_course_average(obj)

    def get_progress_percent(self, obj):
        return calculate_progress_percent(obj)

    def get_needed_to_pass(self, obj):
        return calculate_needed_to_pass(obj)


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = ("id", "course", "title", "score", "max_score", "weight", "date", "created_at")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        score = attrs.get("score")
        max_score = attrs.get("max_score")
        weight = attrs.get("weight")
        if score is not None and max_score is not None and score > max_score:
            raise serializers.ValidationError("score deve ser <= max_score")
        if weight is not None and weight < 0:
            raise serializers.ValidationError("weight deve ser >= 0")
        return attrs


class SemesterCheckinSerializer(serializers.ModelSerializer):
    class Meta:
        model = SemesterCheckin
        fields = ("id", "semester", "created_at", "overall_stress", "comment")
        read_only_fields = ("id", "created_at")
