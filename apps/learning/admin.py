from django.contrib import admin

from learning.models import AcademicDisciplineScore, Achievement, EmotionalCheckin, StudySession, StudyTask


@admin.register(StudyTask)
class StudyTaskAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "institution",
        "title",
        "due_date",
        "completed",
        "completed_at",
        "created_at",
    )
    list_filter = ("completed", "institution")
    search_fields = ("student__email", "student__name", "title")


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "institution",
        "subject",
        "duration_minutes",
        "created_at",
    )
    list_filter = ("institution",)
    search_fields = ("student__email", "student__name", "subject")


@admin.register(EmotionalCheckin)
class EmotionalCheckinAdmin(admin.ModelAdmin):
    list_display = ("student", "institution", "mood", "stress_level", "motivation_level", "created_at")
    list_filter = ("mood", "institution")
    search_fields = ("student__email", "student__name", "notes")


@admin.register(AcademicDisciplineScore)
class AcademicDisciplineScoreAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "institution",
        "score_value",
        "classification",
        "calculated_at",
    )
    list_filter = ("classification", "institution")
    search_fields = ("student__email", "student__name")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("student", "institution", "achievement_type", "title", "unlocked_at")
    list_filter = ("achievement_type", "institution")
    search_fields = ("student__email", "student__name", "title")
