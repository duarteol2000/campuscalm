from django.urls import path

from study_assistant.views import StudyAssistantAskView

urlpatterns = [
    path("ask/", StudyAssistantAskView.as_view(), name="study-assistant-ask"),
]

