from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from onboarding.services import refresh_user_progress
from utils.gating import compute_status


class OnboardingStatusSerializer(serializers.Serializer):
    current_step = serializers.CharField(allow_null=True)
    missing_steps = serializers.ListField(child=serializers.CharField())
    required_actions = serializers.ListField(child=serializers.CharField())


class OnboardingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OnboardingStatusSerializer

    @extend_schema(
        tags=["Onboarding"],
        operation_id="onboarding_status",
        responses={200: OnboardingStatusSerializer},
    )
    def get(self, request):
        progress = refresh_user_progress(request.user)
        current_step, missing_steps, required_actions = compute_status(progress)
        return Response(
            {
                "current_step": current_step,
                "missing_steps": missing_steps,
                "required_actions": required_actions,
            }
        )
