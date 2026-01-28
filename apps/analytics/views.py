from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from agenda.models import CalendarEvent
from mood.models import MoodEntry
from planner.models import Task
from semester.models import Semester
from utils.constants import FEATURE_DASHBOARD_BASIC, FEATURE_REPORTS_ADVANCED, SEMESTER_ACTIVE
from utils.features import has_feature, require_feature


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        require_feature(request.user, FEATURE_DASHBOARD_BASIC)
        now = timezone.now()
        tasks = Task.objects.filter(user=request.user)
        events = CalendarEvent.objects.filter(user=request.user, start_at__gte=now)
        moods = MoodEntry.objects.filter(user=request.user)
        active_semester = Semester.objects.filter(user=request.user, status=SEMESTER_ACTIVE).first()
        return Response(
            {
                "tasks": {
                    "todo": tasks.filter(status="TODO").count(),
                    "doing": tasks.filter(status="DOING").count(),
                    "done": tasks.filter(status="DONE").count(),
                },
                "upcoming_events": events.count(),
                "mood_entries": moods.count(),
                "active_semester": active_semester.name if active_semester else None,
            }
        )


class SemesterAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, semester_id):
        if not has_feature(request.user, FEATURE_REPORTS_ADVANCED):
            return Response({"detail": "Plano atual nao permite analytics avancado."}, status=status.HTTP_403_FORBIDDEN)
        semester = get_object_or_404(Semester, pk=semester_id, user=request.user)
        courses = semester.courses.all()
        return Response(
            {
                "semester": semester.name,
                "courses": [
                    {
                        "title": course.title,
                        "status": course.status,
                        "final_grade": course.final_grade,
                    }
                    for course in courses
                ],
            }
        )
