from django.contrib import admin

from planner.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "due_date", "status")
    list_filter = ("status",)
    search_fields = ("title", "user__email")
