from django.urls import path
from rest_framework.routers import DefaultRouter

from semester.views import AssessmentViewSet, CourseProgressView, CourseViewSet, FinishSemesterView, SemesterViewSet

router = DefaultRouter()
router.register(r"semesters", SemesterViewSet, basename="semesters")
router.register(r"courses", CourseViewSet, basename="courses")
router.register(r"assessments", AssessmentViewSet, basename="assessments")

urlpatterns = router.urls + [
    path("courses/<int:pk>/progress/", CourseProgressView.as_view(), name="course-progress"),
    path("finish/<int:semester_id>/", FinishSemesterView.as_view(), name="semester-finish"),
]
