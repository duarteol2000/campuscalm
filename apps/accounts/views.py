from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import RegisterResponseSerializer, RegisterSerializer, UserSerializer
from billing.models import Plan, UserSubscription
from utils.constants import PLAN_LITE


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(
        tags=["Accounts"],
        operation_id="accounts_register",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=RegisterResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Register response",
                        value={
                            "user": {
                                "id": 1,
                                "email": "test@example.com",
                                "name": "Teste",
                                "phone_number": "",
                                "institution": None,
                                "role": "student",
                                "preferred_language": "pt-BR",
                                "is_active": True,
                                "created_at": "2026-03-12T10:00:00Z",
                                "updated_at": "2026-03-12T10:00:00Z",
                            },
                            "refresh": "jwt-refresh-token",
                            "access": "jwt-access-token",
                        },
                    )
                ],
            )
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        plan = Plan.objects.filter(code=PLAN_LITE, is_active=True).first()
        if plan:
            UserSubscription.objects.get_or_create(user=user, defaults={"plan": plan})
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        operation_id="accounts_me",
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
