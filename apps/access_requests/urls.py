from django.urls import path

from access_requests.views import (
    AccessApproveView,
    AccessRejectView,
    AccessRequestDetailView,
    AccessRequestListCreateView,
    AccessTriageLogView,
)

urlpatterns = [
    path("requests/", AccessRequestListCreateView.as_view(), name="access-request-list-create"),
    path("requests/<int:pk>/", AccessRequestDetailView.as_view(), name="access-request-detail"),
    path("requests/<int:pk>/approve/", AccessApproveView.as_view(), name="access-request-approve"),
    path("requests/<int:pk>/reject/", AccessRejectView.as_view(), name="access-request-reject"),
    path("triage/<int:pk>/log/", AccessTriageLogView.as_view(), name="access-triage-log"),
]
