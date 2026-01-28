from django.contrib import admin

from notifications.models import NotificationQueue


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = ("user", "channel", "status", "scheduled_for")
    list_filter = ("channel", "status")
