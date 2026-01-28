from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from coach_ai.models import CoachLog
from semester.models import Assessment, Course, Semester
from semester.serializers import AssessmentSerializer, CourseSerializer, SemesterSerializer
from utils.academic_progress import (
    calculate_course_average,
    calculate_needed_to_pass,
    calculate_progress_percent,
    update_course_status,
)
from utils.constants import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    COACH_REPROVACAO,
    COACH_SEMESTRE_CONCLUIDO,
    COURSE_FAILED,
    SEMESTER_FINISHED,
)
from utils.gating import gate_course_progress, gate_finish_semester
from utils.messages import (
    MESSAGE_ACHIEVEMENT,
    MESSAGE_CARE,
    MESSAGE_INCENTIVE,
    MESSAGE_WARNING,
    send_message,
)


class SemesterViewSet(viewsets.ModelViewSet):
    serializer_class = SemesterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Semester.objects.filter(user=self.request.user).order_by("-start_date")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(semester__user=self.request.user).order_by("title")

    def perform_create(self, serializer):
        semester = serializer.validated_data["semester"]
        if semester.user != self.request.user:
            raise PermissionDenied("Semestre nao pertence ao usuario")
        serializer.save()


class AssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Assessment.objects.filter(course__semester__user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.semester.user != self.request.user:
            raise PermissionDenied("Curso nao pertence ao usuario")
        previous_progress = calculate_progress_percent(course)
        serializer.save()
        course.refresh_from_db()
        new_progress = calculate_progress_percent(course)
        update_course_status(course, semester_status=course.semester.status)
        course.final_grade = calculate_course_average(course)
        course.save(update_fields=["status", "final_grade"])

        if new_progress > previous_progress:
            send_message(
                self.request.user,
                MESSAGE_INCENTIVE,
                {
                    "event": "assessment_progress_up",
                    "course": course.title,
                    "progress": int(new_progress),
                },
                channels=[CHANNEL_IN_APP, CHANNEL_EMAIL],
            )
        elif new_progress < previous_progress:
            send_message(
                self.request.user,
                MESSAGE_CARE,
                {
                    "event": "assessment_progress_down",
                    "course": course.title,
                    "progress": int(new_progress),
                },
                channels=[CHANNEL_IN_APP, CHANNEL_EMAIL],
            )

        if new_progress >= 100 and previous_progress < 100:
            send_message(
                self.request.user,
                MESSAGE_ACHIEVEMENT,
                {
                    "event": "course_passed",
                    "course": course.title,
                    "progress": int(new_progress),
                },
                channels=[CHANNEL_IN_APP, CHANNEL_EMAIL],
            )

        week_ahead = timezone.localdate() + timedelta(days=7)
        upcoming = course.assessments.filter(date__gte=timezone.localdate(), date__lte=week_ahead).exists()
        if new_progress < 70 and upcoming:
            send_message(
                self.request.user,
                MESSAGE_WARNING,
                {
                    "event": "low_progress_upcoming",
                    "course": course.title,
                    "progress": int(new_progress),
                },
                channels=[CHANNEL_IN_APP, CHANNEL_EMAIL],
            )


class CourseProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk, semester__user=request.user)
        allowed, message = gate_course_progress(course)
        if not allowed:
            return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)
        current_average = calculate_course_average(course)
        progress_percent = calculate_progress_percent(course)
        needed_to_pass = calculate_needed_to_pass(course)
        return Response(
            {
                "course_id": course.id,
                "current_average": current_average,
                "progress_percent": progress_percent,
                "needed_to_pass": needed_to_pass,
            }
        )


class FinishSemesterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, semester_id):
        semester = get_object_or_404(Semester, pk=semester_id, user=request.user)
        allowed, message = gate_finish_semester(semester)
        if not allowed:
            return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)

        any_failed = False
        for course in semester.courses.all():
            current_average = calculate_course_average(course)
            course.final_grade = current_average
            update_course_status(course, semester_status=SEMESTER_FINISHED)
            if course.status == COURSE_FAILED:
                any_failed = True
            course.save(update_fields=["final_grade", "status"])

        semester.status = SEMESTER_FINISHED
        semester.save()

        if any_failed:
            CoachLog.objects.create(
                user=request.user,
                trigger_type=COACH_REPROVACAO,
                suggestion_text=(
                    "Identificamos disciplinas reprovadas. Vamos montar um plano de continuidade e recuperar o ritmo."
                ),
            )
            send_message(
                request.user,
                MESSAGE_CARE,
                {
                    "event": "semester_with_fail",
                    "course": "",
                },
                channels=[CHANNEL_IN_APP, CHANNEL_EMAIL],
            )
            send_message(
                request.user,
                MESSAGE_INCENTIVE,
                {
                    "event": "semester_continue",
                    "course": "",
                },
                channels=[CHANNEL_IN_APP, CHANNEL_EMAIL],
            )
        else:
            CoachLog.objects.create(
                user=request.user,
                trigger_type=COACH_SEMESTRE_CONCLUIDO,
                suggestion_text=(
                    "Parabens! Voce concluiu o semestre sem reprovacoes. Continue com esse ritmo."
                ),
            )
            send_message(
                request.user,
                MESSAGE_ACHIEVEMENT,
                {
                    "event": "semester_all_passed",
                    "course": "",
                },
                channels=["IN_APP", "EMAIL"],
            )

        return Response({"detail": "Semestre finalizado."})
