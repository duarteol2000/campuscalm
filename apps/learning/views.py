from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasInstitutionAccess, has_same_institution
from learning.serializers import (
    ClassHeatmapEntrySerializer,
    ClassTrendResponseSerializer,
    DashboardQuerySerializer,
    InstitutionDashboardSerializer,
    ParentDashboardSerializer,
    StudentDashboardSerializer,
    TeacherDashboardSerializer,
)
from learning.services.dashboards import (
    class_heatmap_dashboard,
    class_trend_dashboard,
    institution_dashboard,
    parent_dashboard,
    resolve_accessible_class_group,
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

    def _resolve_class_group(self, request, class_id):
        class_group = resolve_accessible_class_group(request.user, class_id)
        if class_group is None:
            return None, Response({"detail": "Turma fora do escopo do usuario."}, status=status.HTTP_403_FORBIDDEN)
        return class_group, None


class StudentDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_STUDENT}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_student_dashboard",
        description="Retorna o dashboard comportamental do aluno autenticado. Permissão: `student` com assinatura institucional válida.",
        responses={200: OpenApiResponse(response=StudentDashboardSerializer)},
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
        description="Retorna o dashboard pedagógico. `teacher` vê apenas turmas atribuídas; `coordinator` e `institution_admin` veem toda a instituição.",
        parameters=[DashboardQuerySerializer],
        responses={
            200: OpenApiResponse(
                response=TeacherDashboardSerializer,
                examples=[
                    OpenApiExample(
                        "Teacher dashboard",
                        value={
                            "my_classes": [
                                {
                                    "class_id": 1,
                                    "class_name": "1A",
                                    "grade_level": "Ensino Medio",
                                    "student_count": 6,
                                    "avg_score": 652.5,
                                }
                            ],
                            "average_by_class": [
                                {
                                    "class_id": 1,
                                    "class_name": "1A",
                                    "grade_level": "Ensino Medio",
                                    "student_count": 6,
                                    "avg_score": 652.5,
                                }
                            ],
                            "class_average": 652.5,
                            "students_at_risk": [],
                            "students_low_consistency": [],
                            "students_good_discipline": [],
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
                            "ranking_filters": {"class_group": "1A", "search": ""},
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
        institution_id, institution_denied = self._resolve_institution_id(request, serializer.validated_data.get("institution_id"))
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
        institution_id, institution_denied = self._resolve_institution_id(request, serializer.validated_data.get("institution_id"))
        if institution_denied:
            return institution_denied
        payload = institution_dashboard(request.user, institution_id=institution_id)
        return Response(InstitutionDashboardSerializer(payload).data)


class ClassTrendDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_TEACHER, User.ROLE_COORDINATOR, User.ROLE_INSTITUTION_ADMIN}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_class_trend_dashboard",
        description="Retorna a média das últimas 8 semanas para uma turma específica. `teacher` só acessa turmas atribuídas.",
        parameters=[
            OpenApiParameter(name="class_id", type=int, location=OpenApiParameter.PATH, required=True),
        ],
        responses={
            200: OpenApiResponse(
                response=ClassTrendResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Class trend",
                        value={
                            "class_id": 1,
                            "class_name": "1A",
                            "weeks": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"],
                            "avg_score": [520, 560, 610, 650, 690, 710, 730, 742],
                        },
                    )
                ],
            )
        },
    )
    def get(self, request, class_id: int):
        denied = self._ensure_role(request)
        if denied:
            return denied
        class_group, class_denied = self._resolve_class_group(request, class_id)
        if class_denied:
            return class_denied
        payload = class_trend_dashboard(request.user, class_group)
        return Response(ClassTrendResponseSerializer(payload).data)


class ClassHeatmapDashboardView(_RoleDashboardBaseView):
    allowed_roles = {User.ROLE_TEACHER, User.ROLE_COORDINATOR, User.ROLE_INSTITUTION_ADMIN}

    @extend_schema(
        tags=["Learning Dashboards"],
        operation_id="learning_class_heatmap_dashboard",
        description="Retorna o heatmap de risco da turma. `teacher` só acessa turmas atribuídas.",
        parameters=[
            OpenApiParameter(name="class_id", type=int, location=OpenApiParameter.PATH, required=True),
        ],
        responses={
            200: OpenApiResponse(
                response=ClassHeatmapEntrySerializer(many=True),
                examples=[
                    OpenApiExample(
                        "Class heatmap",
                        value=[
                            {"student_id": 1, "name": "Ana Luisa", "score": 820, "level": "green"},
                            {"student_id": 2, "name": "Leandro Jared", "score": 610, "level": "yellow"},
                            {"student_id": 3, "name": "Fernanda", "score": 430, "level": "orange"},
                        ],
                    )
                ],
            )
        },
    )
    def get(self, request, class_id: int):
        denied = self._ensure_role(request)
        if denied:
            return denied
        class_group, class_denied = self._resolve_class_group(request, class_id)
        if class_denied:
            return class_denied
        payload = class_heatmap_dashboard(request.user, class_group)
        serializer = ClassHeatmapEntrySerializer(payload, many=True)
        return Response(serializer.data)
