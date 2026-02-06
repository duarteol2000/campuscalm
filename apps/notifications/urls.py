from django.urls import path

from . import views

urlpatterns = [
    path("test-email/", views.TestEmailView.as_view(), name="notifications-test-email"),
    path("pending/", views.PendingNotificationsView.as_view(), name="notifications-pending"),
    path("whatsapp/webhook/", views.whatsapp_webhook_view, name="notifications-whatsapp-webhook"),
]
