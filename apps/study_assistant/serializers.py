from rest_framework import serializers


class StudyAssistantAskSerializer(serializers.Serializer):
    message = serializers.CharField()
    institution_id = serializers.IntegerField(required=False)


class StudyAssistantResponseSerializer(serializers.Serializer):
    intent = serializers.CharField()
    subject = serializers.CharField(allow_null=True)
    language = serializers.CharField()
    message = serializers.CharField()
