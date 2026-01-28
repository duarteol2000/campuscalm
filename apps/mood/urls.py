from django.urls import path

from mood.views import MoodEntryListCreateView, MoodWeeklySummaryView

urlpatterns = [
    path("entries/", MoodEntryListCreateView.as_view(), name="mood-entries"),
    path("summary/weekly/", MoodWeeklySummaryView.as_view(), name="mood-summary-weekly"),
]
