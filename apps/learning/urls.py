from django.urls import path

from learning.views import (
    ClassHeatmapDashboardView,
    ClassTrendDashboardView,
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
    path("dashboard/class-trend/<int:class_id>/", ClassTrendDashboardView.as_view(), name="learning-dashboard-class-trend"),
    path("dashboard/class-heatmap/<int:class_id>/", ClassHeatmapDashboardView.as_view(), name="learning-dashboard-class-heatmap"),
]
