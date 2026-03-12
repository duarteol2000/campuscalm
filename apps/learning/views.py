from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasInstitutionAccess, has_same_institution
from learning.serializers import (
    DashboardQuerySerializer,
    InstitutionDashboardSerializer,
    ParentDashboardSerializer,
    StudentDashboardSerializer,
    TeacherDashboardSerializer,
)
from learning.services.dashboards import (
    institution_dashboard,
    parent_dashboard,
    student_dashboard,
    teacher_dashboard,
)


class _RoleDashboardBaseView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasInstitutionAccess]
    allowed_roles = set()

    def _ensure_role(self, request):
        if request.user.is_superuser:
            return None
        if request.user.role not in self.allowed_roles:
            return Response({"detail": "Permissao insuficiente."}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _resolve_institution_id(self, request, institution_id):
        resolved_id = institution_id or request.user.institution_id
        if request.user.is_superuser:
            return resolved_id, None
        if not has_same_institution(request.user, resolved_id):
            return None, Response({"detail": "Instituicao fora do escopo do usuario."}, status=status.HTTP_403_FORBIDDEN)
        return resolved_id, None


class StudentDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_STUDENT}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_student_dashboard",
        description="Retorna o dashboard comportamental do aluno autenticado. Permissão: `student` com assinatura institucional válida.",
        responses={
            200: OpenApiResponse(
                response=StudentDashboardSerializer,
                examples=[
                    OpenApiExample(
                        "Student dashboard",
                        value={
                            "score_current": {
                                "score_value": 720,
                                "classification": "disciplinado",
                                "calculated_at": "2026-03-12T10:00:00Z",
                            },
                            "score_evolution": [
                                {
                                    "score_value": 680,
                                    "classification": "organizado",
                                    "calculated_at": "2026-03-05T10:00:00Z",
                                }
                            ],
                            "tasks_pending": [{"id": 1, "title": "Lista 1", "due_date": "2026-03-15"}],
                            "tasks_completed": [],
                            "study_consistency": {
                                "sessions_last_7_days": 4,
                                "study_days_last_30_days": 12,
                                "current_streak_days": 3,
                            },
                            "achievements": [],
                            "friendly_alerts": ["Sua consistência de estudo está baixa nesta semana."],
                            "recommendations": ["Comece com sessões de 25 minutos e pausas curtas de 5 minutos para reconstruir o hábito."],
                        },
                    )
                ],
            )
        },
    )
    def get(self, request):
        denied = self._ensure_role(request)
        if denied:
            return denied
        payload = student_dashboard(request.user)
        return Response(StudentDashboardSerializer(payload).data)


class ParentDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_PARENT}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_parent_dashboard",
        description="Retorna o dashboard do responsável com os filhos vinculados. Permissão: `parent` com assinatura institucional válida.",
        responses={200: ParentDashboardSerializer},
    )
    def get(self, request):
        denied = self._ensure_role(request)
        if denied:
            return denied
        payload = parent_dashboard(request.user)
        return Response(ParentDashboardSerializer(payload).data)


class TeacherDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_TEACHER, User.ROLE_COORDINATOR, User.ROLE_INSTITUTION_ADMIN}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_teacher_dashboard",
        description="Retorna o dashboard pedagógico da turma. Permissão: `teacher`, `coordinator` ou `institution_admin` no escopo da própria instituição.",
        parameters=[DashboardQuerySerializer],
        responses={
            200: OpenApiResponse(
                response=TeacherDashboardSerializer,
                examples=[
                    OpenApiExample(
                        "Teacher dashboard",
                        value={
                            "class_average": 652.5,
                            "students_at_risk": [],
                            "students_low_consistency": [],
                            "students_good_discipline": [
                                {
                                    "student_id": 10,
                                    "student_name": "Ana",
                                    "class_group": "A",
                                    "score_value": 780,
                                    "classification": "disciplinado",
                                    "weekly_sessions": 5,
                                    "overdue_tasks": 0,
                                    "high_stress_events": 0,
                                }
                            ],
                            "pedagogical_insights": ["Há alunos com baixa consistência de estudo nesta turma."],
                            "ranking": [],
                            "ranking_pagination": {
                                "page": 1,
                                "page_size": 10,
                                "total_items": 1,
                                "total_pages": 1,
                                "has_next": False,
                                "has_previous": False,
                            },
                            "ranking_filters": {"class_group": "A", "search": ""},
                            "distribution": [{"classification": "disciplinado", "total": 3}],
                        },
                    )
                ],
            )
        },
    )
    def get(self, request):
        denied = self._ensure_role(request)
        if denied:
            return denied
        serializer = DashboardQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        institution_id, institution_denied = self._resolve_institution_id(
            request,
            serializer.validated_data.get("institution_id"),
        )
        if institution_denied:
            return institution_denied
        payload = teacher_dashboard(
            request.user,
            institution_id=institution_id,
            class_group=serializer.validated_data.get("class_group") or None,
            search=serializer.validated_data.get("search") or None,
            page=serializer.validated_data.get("page") or 1,
            page_size=serializer.validated_data.get("page_size") or 10,
        )
        return Response(TeacherDashboardSerializer(payload).data)


class InstitutionDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_COORDINATOR, User.ROLE_INSTITUTION_ADMIN}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_institution_dashboard",
        description="Retorna a visão consolidada da instituição. Permissão: `coordinator` ou `institution_admin` no escopo da própria instituição.",
        parameters=[DashboardQuerySerializer],
        responses={200: InstitutionDashboardSerializer},
    )
    def get(self, request):
        denied = self._ensure_role(request)
        if denied:
            return denied
        serializer = DashboardQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        institution_id, institution_denied = self._resolve_institution_id(
            request,
            serializer.validated_data.get("institution_id"),
        )
        if institution_denied:
            return institution_denied
        payload = institution_dashboard(request.user, institution_id=institution_id)
        return Response(InstitutionDashboardSerializer(payload).data)
