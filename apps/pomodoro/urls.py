from django.urls import path

from pomodoro.views import PomodoroStartView, PomodoroStopView, PomodoroWeeklySummaryView

urlpatterns = [
    path("start/", PomodoroStartView.as_view(), name="pomodoro-start"),
    path("stop/<int:pk>/", PomodoroStopView.as_view(), name="pomodoro-stop"),
    path("summary/weekly/", PomodoroWeeklySummaryView.as_view(), name="pomodoro-summary-weekly"),
]
