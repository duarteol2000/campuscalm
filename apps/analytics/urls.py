from django.urls import path

from analytics.views import DashboardView, SemesterAnalyticsView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="analytics-dashboard"),
    path("semester/<int:semester_id>/", SemesterAnalyticsView.as_view(), name="analytics-semester"),
]
