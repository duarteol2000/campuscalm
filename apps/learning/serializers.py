from rest_framework import serializers


class DashboardQuerySerializer(serializers.Serializer):
    class_group = serializers.CharField(required=False, allow_blank=True)
    institution_id = serializers.IntegerField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=10)


class ScoreSnapshotSerializer(serializers.Serializer):
    score_value = serializers.IntegerField()
    classification = serializers.CharField()
    calculated_at = serializers.DateTimeField()


class ScoreEvolutionEntrySerializer(ScoreSnapshotSerializer):
    pass


class StudyTaskPendingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    due_date = serializers.DateField()


class StudyTaskCompletedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    completed_at = serializers.DateTimeField()


class StudyConsistencySerializer(serializers.Serializer):
    sessions_last_7_days = serializers.IntegerField()
    study_days_last_30_days = serializers.IntegerField()
    current_streak_days = serializers.IntegerField()


class AchievementSerializer(serializers.Serializer):
    achievement_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    unlocked_at = serializers.DateTimeField()


class StudentDashboardSerializer(serializers.Serializer):
    score_current = ScoreSnapshotSerializer()
    score_evolution = ScoreEvolutionEntrySerializer(many=True)
    tasks_pending = StudyTaskPendingSerializer(many=True)
    tasks_completed = StudyTaskCompletedSerializer(many=True)
    study_consistency = StudyConsistencySerializer()
    achievements = AchievementSerializer(many=True)
    friendly_alerts = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())


class ParentChildDashboardSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    relationship_type = serializers.CharField()
    score_current = ScoreSnapshotSerializer()
    study_consistency = StudyConsistencySerializer()
    tasks_completed = StudyTaskCompletedSerializer(many=True)
    friendly_alerts = serializers.ListField(child=serializers.CharField())


class ParentDashboardSerializer(serializers.Serializer):
    children = ParentChildDashboardSerializer(many=True)


class DisciplineDistributionEntrySerializer(serializers.Serializer):
    classification = serializers.CharField()
    total = serializers.IntegerField()


class TeacherStudentRowSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    class_group = serializers.CharField(allow_blank=True)
    score_value = serializers.IntegerField()
    classification = serializers.CharField()
    weekly_sessions = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    high_stress_events = serializers.IntegerField()


class TeacherRankingPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()


class TeacherRankingFiltersSerializer(serializers.Serializer):
    class_group = serializers.CharField(allow_blank=True)
    search = serializers.CharField(allow_blank=True)


class TeacherDashboardSerializer(serializers.Serializer):
    class_average = serializers.FloatField()
    students_at_risk = TeacherStudentRowSerializer(many=True)
    students_low_consistency = TeacherStudentRowSerializer(many=True)
    students_good_discipline = TeacherStudentRowSerializer(many=True)
    pedagogical_insights = serializers.ListField(child=serializers.CharField())
    ranking = TeacherStudentRowSerializer(many=True)
    ranking_pagination = TeacherRankingPaginationSerializer()
    ranking_filters = TeacherRankingFiltersSerializer()
    distribution = DisciplineDistributionEntrySerializer(many=True)


class InstitutionClassRankingSerializer(serializers.Serializer):
    class_group = serializers.CharField()
    average_score = serializers.FloatField()
    students_total = serializers.IntegerField()


class InstitutionStudentRowSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    class_group = serializers.CharField()
    score_value = serializers.IntegerField()
    classification = serializers.CharField()


class InstitutionDashboardSerializer(serializers.Serializer):
    institution_average = serializers.FloatField()
    average_by_class = InstitutionClassRankingSerializer(many=True)
    students_at_risk = InstitutionStudentRowSerializer(many=True)
    class_ranking = InstitutionClassRankingSerializer(many=True)
    discipline_distribution = DisciplineDistributionEntrySerializer(many=True)
    top_students = InstitutionStudentRowSerializer(many=True)
    pedagogical_insights = serializers.ListField(child=serializers.CharField())
