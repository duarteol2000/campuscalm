from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "phone_number",
            "institution",
            "role",
            "preferred_language",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "phone_number",
            "preferred_language",
            "password",
        )

    def validate(self, attrs):
        allowed_fields = set(self.fields.keys())
        provided_fields = set(getattr(self, "initial_data", {}).keys())
        extra_fields = provided_fields - allowed_fields
        if extra_fields:
            raise serializers.ValidationError({field: "This field is not allowed." for field in sorted(extra_fields)})
        return super().validate(attrs)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, role=User.ROLE_STUDENT, **validated_data)
        return user
