from django.urls import path

from notifications.views import PendingNotificationsView, TestEmailView

urlpatterns = [
    path("test-email/", TestEmailView.as_view(), name="notifications-test-email"),
    path("pending/", PendingNotificationsView.as_view(), name="notifications-pending"),
]
