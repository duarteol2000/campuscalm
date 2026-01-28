from rest_framework import serializers

from access_requests.models import AccessRequest, AITriageLog
from utils.constants import ACCESS_APPROVED, ACCESS_REJECTED


class AccessRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRequest
        fields = (
            "id",
            "requester_email",
            "requester_name",
            "requester_type",
            "institution_name",
            "estimated_users",
            "wants_features",
            "message",
            "status",
            "recommended_plan",
            "created_at",
        )
        read_only_fields = ("id", "status", "recommended_plan", "created_at")


class AccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRequest
        fields = "__all__"


class AITriageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITriageLog
        fields = ("id", "model_name", "input_payload", "output_payload", "created_at")
        read_only_fields = fields


class AccessDecisionSerializer(serializers.Serializer):
    decided_plan = serializers.CharField(required=False)

    def validate_decided_plan(self, value):
        if value and value not in {"LITE", "PRO"}:
            raise serializers.ValidationError("Plano invalido")
        return value
