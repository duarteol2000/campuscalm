from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Plan, UserSubscription
from billing.serializers import PlanSerializer, SetPlanSerializer, UserSubscriptionSerializer
from utils.constants import PLAN_LITE

User = get_user_model()


class CurrentPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        subscription = UserSubscription.objects.filter(user=request.user, is_active=True).select_related("plan").first()
        if subscription:
            return Response(UserSubscriptionSerializer(subscription).data)
        plan = Plan.objects.filter(code=PLAN_LITE, is_active=True).first()
        if not plan:
            return Response({"detail": "Plano nao configurado."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"plan": PlanSerializer(plan).data, "started_at": None, "is_active": False})


class SetPlanView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = SetPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(id=serializer.validated_data["user_id"])
        plan = Plan.objects.get(code=serializer.validated_data["plan_code"])
        subscription, _ = UserSubscription.objects.get_or_create(user=user, defaults={"plan": plan})
        subscription.plan = plan
        subscription.is_active = True
        subscription.save()
        return Response(UserSubscriptionSerializer(subscription).data)
