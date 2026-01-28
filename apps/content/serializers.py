from rest_framework import serializers

from content.models import GuidedContent


class GuidedContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuidedContent
        fields = ("id", "title", "category", "duration_minutes", "body_text", "is_premium", "created_at")
        read_only_fields = ("id", "created_at")
