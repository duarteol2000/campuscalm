from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import NotificationQueue
from notifications.serializers import NotificationQueueSerializer
from utils.constants import CHANNEL_EMAIL, NOTIF_PENDING
from utils.features import has_feature
from utils.constants import FEATURE_EMAIL_NOTIFICATIONS


class TestEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not has_feature(request.user, FEATURE_EMAIL_NOTIFICATIONS):
            return Response({"detail": "Plano atual nao permite email."}, status=status.HTTP_403_FORBIDDEN)
        subject = "Campus Calm - Teste de Email"
        message = "Este e um email de teste do Campus Calm."
        send_mail(subject, message, None, [request.user.email])
        return Response({"detail": "Email enviado para console."})


class PendingNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        pending = NotificationQueue.objects.filter(
            user=request.user, status=NOTIF_PENDING, scheduled_for__lte=now
        ).order_by("scheduled_for")
        return Response(NotificationQueueSerializer(pending, many=True).data)
