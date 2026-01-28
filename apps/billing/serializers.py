from rest_framework import serializers

from billing.models import Plan, UserSubscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ("code", "name", "description", "features")


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()

    class Meta:
        model = UserSubscription
        fields = ("plan", "started_at", "is_active")


class SetPlanSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    plan_code = serializers.CharField()
