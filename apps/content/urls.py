from django.urls import path

from content.views import GuidedContentDetailView, GuidedContentListView

urlpatterns = [
    path("guided/", GuidedContentListView.as_view(), name="guided-content"),
    path("guided/<int:pk>/", GuidedContentDetailView.as_view(), name="guided-content-detail"),
]
