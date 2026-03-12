from django.urls import path

from learning.views import (
    InstitutionDashboardView,
    ParentDashboardView,
    StudentDashboardView,
    TeacherDashboardView,
)

urlpatterns = [
    path("dashboard/student/", StudentDashboardView.as_view(), name="learning-dashboard-student"),
    path("dashboard/parent/", ParentDashboardView.as_view(), name="learning-dashboard-parent"),
    path("dashboard/teacher/", TeacherDashboardView.as_view(), name="learning-dashboard-teacher"),
    path("dashboard/institution/", InstitutionDashboardView.as_view(), name="learning-dashboard-institution"),
]

