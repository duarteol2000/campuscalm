from rest_framework import serializers


class DashboardTaskCountersSerializer(serializers.Serializer):
    todo = serializers.IntegerField()
    doing = serializers.IntegerField()
    done = serializers.IntegerField()


class DashboardAnalyticsSerializer(serializers.Serializer):
    tasks = DashboardTaskCountersSerializer()
    upcoming_events = serializers.IntegerField()
    mood_entries = serializers.IntegerField()
    active_semester = serializers.CharField(allow_null=True)


class SemesterAnalyticsCourseSerializer(serializers.Serializer):
    title = serializers.CharField()
    status = serializers.CharField()
    final_grade = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)


class SemesterAnalyticsSerializer(serializers.Serializer):
    semester = serializers.CharField()
    courses = SemesterAnalyticsCourseSerializer(many=True)
