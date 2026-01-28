from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from access_requests.models import AccessRequest, AITriageLog
from access_requests.serializers import (
    AccessDecisionSerializer,
    AccessRequestCreateSerializer,
    AccessRequestSerializer,
    AITriageLogSerializer,
)
from utils.constants import ACCESS_APPROVED, ACCESS_REJECTED
from utils.triage import TRIAGE_MODEL_NAME, run_triage


class AccessRequestListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get(self, request):
        requests = AccessRequest.objects.all().order_by("-created_at")
        return Response(AccessRequestSerializer(requests, many=True).data)

    def post(self, request):
        serializer = AccessRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_request = serializer.save()
        triage_result = run_triage(access_request)
        recommended_plan = triage_result["recommended_plan"]
        access_request.recommended_plan = recommended_plan
        access_request.save(update_fields=["recommended_plan"])
        input_payload = serializer.validated_data
        output_payload = triage_result["output_payload"]
        AITriageLog.objects.create(
            access_request=access_request,
            model_name=TRIAGE_MODEL_NAME,
            input_payload=input_payload,
            output_payload=output_payload,
        )
        return Response(AccessRequestCreateSerializer(access_request).data, status=status.HTTP_201_CREATED)


class AccessRequestDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        access_request = get_object_or_404(AccessRequest, pk=pk)
        return Response(AccessRequestSerializer(access_request).data)


class AccessApproveView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        access_request = get_object_or_404(AccessRequest, pk=pk)
        serializer = AccessDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_request.status = ACCESS_APPROVED
        access_request.decided_plan = serializer.validated_data.get("decided_plan") or access_request.recommended_plan
        access_request.save(update_fields=["status", "decided_plan"])
        return Response(AccessRequestSerializer(access_request).data)


class AccessRejectView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        access_request = get_object_or_404(AccessRequest, pk=pk)
        access_request.status = ACCESS_REJECTED
        access_request.save(update_fields=["status"])
        return Response(AccessRequestSerializer(access_request).data)


class AccessTriageLogView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        access_request = get_object_or_404(AccessRequest, pk=pk)
        log = access_request.triage_logs.order_by("-created_at").first()
        if not log:
            return Response({"detail": "Sem log de triagem."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AITriageLogSerializer(log).data)
