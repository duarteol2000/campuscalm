from django.contrib import admin

from mood.models import MoodEntry


@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "mood", "created_at")
    list_filter = ("mood",)
    search_fields = ("user__email",)
