from django.contrib import admin

from agenda.models import CalendarEvent, ReminderRule


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "event_type", "start_at")
    list_filter = ("event_type",)
    search_fields = ("title", "user__email")


@admin.register(ReminderRule)
class ReminderRuleAdmin(admin.ModelAdmin):
    list_display = ("user", "target_type", "remind_before_minutes", "is_active")
    list_filter = ("target_type", "is_active")
