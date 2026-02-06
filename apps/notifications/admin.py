from django.contrib import admin

from notifications.models import IncomingMessage, NotificationQueue


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = ("user", "channel", "status", "action_taken", "scheduled_for", "sent_at", "attempts")
    list_filter = ("channel", "status", "action_taken")


@admin.register(IncomingMessage)
class IncomingMessageAdmin(admin.ModelAdmin):
    list_display = ("phone_from", "parsed_action", "received_at", "matched_notification")
    list_filter = ("parsed_action",)
