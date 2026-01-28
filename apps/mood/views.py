from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView

from mood.models import MoodEntry
from mood.serializers import MoodEntrySerializer
from utils.constants import FEATURE_MOOD_BASIC, MOOD_VERY_BAD
from utils.features import require_feature


class MoodEntryListCreateView(ListCreateAPIView):
    serializer_class = MoodEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        require_feature(self.request.user, FEATURE_MOOD_BASIC)
        return MoodEntry.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        require_feature(self.request.user, FEATURE_MOOD_BASIC)
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        week_ago = timezone.now() - timedelta(days=7)
        very_bad_count = MoodEntry.objects.filter(
            user=request.user, mood=MOOD_VERY_BAD, created_at__gte=week_ago
        ).count()
        if very_bad_count >= 3:
            response.data["wellness_notice"] = (
                "Percebemos humor muito baixo recorrente. Procure apoio profissional."
                " No Brasil, o CVV atende 188 (24h)."
            )
        return response


class MoodWeeklySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        require_feature(request.user, FEATURE_MOOD_BASIC)
        week_ago = timezone.now() - timedelta(days=7)
        entries = MoodEntry.objects.filter(user=request.user, created_at__gte=week_ago)
        summary = {}
        for mood, _label in MoodEntry._meta.get_field("mood").choices:
            summary[mood] = entries.filter(mood=mood).count()
        return Response({"summary": summary})
