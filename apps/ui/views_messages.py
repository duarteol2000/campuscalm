from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from notifications.models import NotificationQueue
from utils.constants import CHANNEL_CHOICES, NOTIFICATION_STATUS_CHOICES


@login_required(login_url="/login/")
def message_list_view(request):
    status_filter = request.GET.get("status", "")
    channel_filter = request.GET.get("channel", "")

    notifications = NotificationQueue.objects.filter(user=request.user)
    if status_filter:
        notifications = notifications.filter(status=status_filter)
    if channel_filter:
        notifications = notifications.filter(channel=channel_filter)

    notifications = notifications.order_by("-scheduled_for", "-created_at")

    return render(
        request,
        "ui/messages/message_list.html",
        {
            "notifications": notifications,
            "status_filter": status_filter,
            "channel_filter": channel_filter,
            "status_choices": NOTIFICATION_STATUS_CHOICES,
            "channel_choices": CHANNEL_CHOICES,
        },
    )
