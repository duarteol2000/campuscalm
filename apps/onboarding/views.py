from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from onboarding.services import refresh_user_progress
from utils.gating import compute_status


class OnboardingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
