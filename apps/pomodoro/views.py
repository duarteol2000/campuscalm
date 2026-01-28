from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pomodoro.models import PomodoroSession
from pomodoro.serializers import PomodoroSessionSerializer
from utils.constants import FEATURE_POMODORO_BASIC, POMODORO_COMPLETED, POMODORO_STOPPED
from utils.features import require_feature


class PomodoroStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        require_feature(request.user, FEATURE_POMODORO_BASIC)
        focus_minutes = int(request.data.get("focus_minutes", 25))
        break_minutes = int(request.data.get("break_minutes", 5))
        session = PomodoroSession.objects.create(
            user=request.user,
            focus_minutes=focus_minutes,
            break_minutes=break_minutes,
        )
        return Response(PomodoroSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class PomodoroStopView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        require_feature(request.user, FEATURE_POMODORO_BASIC)
        session = PomodoroSession.objects.get(pk=pk, user=request.user)
        completed_value = request.data.get("completed", False)
        completed = str(completed_value).lower() in {"1", "true", "yes", "on"}
        session.ended_at = timezone.now()
        session.status = POMODORO_COMPLETED if completed else POMODORO_STOPPED
        session.save()
        return Response(PomodoroSessionSerializer(session).data)


class PomodoroWeeklySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        require_feature(request.user, FEATURE_POMODORO_BASIC)
        week_ago = timezone.now() - timedelta(days=7)
        sessions = PomodoroSession.objects.filter(user=request.user, started_at__gte=week_ago)
        total_sessions = sessions.count()
        total_focus_minutes = sum(session.focus_minutes for session in sessions)
        return Response(
            {
                "total_sessions": total_sessions,
                "total_focus_minutes": total_focus_minutes,
            }
        )
