from django.urls import path

from brain.views import WidgetChatContextView, WidgetChatView

urlpatterns = [
    path("chat/context/", WidgetChatContextView.as_view(), name="widget-chat-context"),
    path("chat/", WidgetChatView.as_view(), name="widget-chat"),
]
