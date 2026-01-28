from django.contrib import admin

from semester.models import Assessment, Course, Semester, SemesterCheckin


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "status", "start_date", "end_date")
    list_filter = ("status",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "semester", "status", "passing_grade", "final_grade")
    list_filter = ("status",)


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "score", "max_score", "weight")


@admin.register(SemesterCheckin)
class SemesterCheckinAdmin(admin.ModelAdmin):
    list_display = ("semester", "overall_stress", "created_at")
