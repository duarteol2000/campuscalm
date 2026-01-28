from rest_framework import permissions, viewsets

from planner.models import Task
from planner.serializers import TaskSerializer
from utils.constants import FEATURE_PLANNER_BASIC
from utils.features import require_feature


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
