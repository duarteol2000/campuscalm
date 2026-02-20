from django.urls import path

from . import views

urlpatterns = [
    path("test-email/", views.TestEmailView.as_view(), name="notifications-test-email"),
    path("pending/", views.PendingNotificationsView.as_view(), name="notifications-pending"),
    path("in-app/unread-count/", views.InAppUnreadCountView.as_view(), name="notifications-in-app-unread-count"),
    path("in-app/latest/", views.InAppLatestListView.as_view(), name="notifications-in-app-latest"),
    path("in-app/<int:pk>/mark-read/", views.InAppMarkReadView.as_view(), name="notifications-in-app-mark-read"),
    path("in-app/mark-all-read/", views.InAppMarkAllReadView.as_view(), name="notifications-in-app-mark-all-read"),
    path("whatsapp/webhook/", views.whatsapp_webhook_view, name="notifications-whatsapp-webhook"),
]
