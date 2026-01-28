from django.contrib import admin

from pomodoro.models import PomodoroSession


@admin.register(PomodoroSession)
class PomodoroSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "started_at", "ended_at")
    list_filter = ("status",)
