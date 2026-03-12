from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from planner.models import Task
from planner.serializers import TaskSerializer
from utils.constants import FEATURE_PLANNER_BASIC
from utils.features import require_feature


@extend_schema_view(
    retrieve=extend_schema(
        tags=["Planner"],
        operation_id="planner_tasks_retrieve",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    ),
    update=extend_schema(
        tags=["Planner"],
        operation_id="planner_tasks_update",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    ),
    partial_update=extend_schema(
        tags=["Planner"],
        operation_id="planner_tasks_partial_update",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    ),
    destroy=extend_schema(
        tags=["Planner"],
        operation_id="planner_tasks_destroy",
        parameters=[OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    ),
    list=extend_schema(tags=["Planner"], operation_id="planner_tasks_list"),
    create=extend_schema(tags=["Planner"], operation_id="planner_tasks_create"),
)
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        require_feature(request.user, FEATURE_PLANNER_BASIC)
        return super().initial(request, *args, **kwargs)

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
