from django.urls import path

from brain.views import WidgetChatView

urlpatterns = [
    path("chat/", WidgetChatView.as_view(), name="widget-chat"),
]
