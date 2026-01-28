from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import GuidedContent
from content.serializers import GuidedContentSerializer
from utils.constants import FEATURE_CONTENT_FULL, FEATURE_CONTENT_LIMITED
from utils.features import has_feature


class GuidedContentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not has_feature(request.user, FEATURE_CONTENT_FULL) and not has_feature(request.user, FEATURE_CONTENT_LIMITED):
            return Response({"detail": "Plano atual nao permite conteudos."}, status=status.HTTP_403_FORBIDDEN)
        queryset = GuidedContent.objects.all().order_by("-created_at")
        if not has_feature(request.user, FEATURE_CONTENT_FULL):
            queryset = queryset.filter(is_premium=False)
        return Response(GuidedContentSerializer(queryset, many=True).data)


class GuidedContentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        content = get_object_or_404(GuidedContent, pk=pk)
        if content.is_premium and not has_feature(request.user, FEATURE_CONTENT_FULL):
            return Response({"detail": "Plano atual nao permite este conteudo."}, status=status.HTTP_403_FORBIDDEN)
        return Response(GuidedContentSerializer(content).data)
