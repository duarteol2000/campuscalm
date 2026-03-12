from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
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

    @extend_schema_field(OpenApiTypes.NUMBER)
    def get_current_average(self, obj) -> Decimal:
        return calculate_course_average(obj)

    @extend_schema_field(OpenApiTypes.NUMBER)
    def get_progress_percent(self, obj) -> float:
        return calculate_progress_percent(obj)

    @extend_schema_field(OpenApiTypes.NUMBER)
    def get_needed_to_pass(self, obj) -> Decimal:
        return calculate_needed_to_pass(obj)


class CourseProgressSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    current_average = serializers.DecimalField(max_digits=5, decimal_places=2)
    progress_percent = serializers.FloatField()
    needed_to_pass = serializers.DecimalField(max_digits=5, decimal_places=2)


class SemesterFinishResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class EmptySerializer(serializers.Serializer):
    pass


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
