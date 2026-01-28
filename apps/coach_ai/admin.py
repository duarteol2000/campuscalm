from django.contrib import admin

from coach_ai.models import CoachLog


@admin.register(CoachLog)
class CoachLogAdmin(admin.ModelAdmin):
    list_display = ("user", "trigger_type", "created_at")
    list_filter = ("trigger_type",)
