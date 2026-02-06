import json
import re
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import IncomingMessage, NotificationQueue
from notifications.serializers import NotificationQueueSerializer
from notifications.services.whatsapp_service import send_whatsapp_message_raw
from utils.constants import (
    ACTION_CANCELED,
    ACTION_CONFIRMED,
    ACTION_DELAYED,
    ACTION_NONE,
    CHANNEL_EMAIL,
    CHANNEL_WHATSAPP,
    NOTIF_PENDING,
    NOTIF_SENT,
)
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


# Bloco: Webhook WhatsApp Cloud
@csrf_exempt
def whatsapp_webhook_view(request):
    if request.method == "GET":
        verify_token = request.GET.get("hub.verify_token", "")
        challenge = request.GET.get("hub.challenge", "")
        if verify_token and verify_token == getattr(settings, "WHATSAPP_VERIFY_TOKEN", ""):
            return HttpResponse(challenge, status=200)
        return HttpResponseForbidden("Token invalido.")

    if request.method != "POST":
        return JsonResponse({"detail": "Metodo nao permitido."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    phone_from, text_body = _extract_whatsapp_message(payload)
    parsed_action = _parse_action(text_body)
    matched_notification = _match_notification(phone_from, text_body)

    incoming = IncomingMessage.objects.create(
        phone_from=phone_from or "",
        text=text_body or "",
        raw_payload=payload,
        parsed_action=parsed_action,
        matched_notification=matched_notification,
    )

    if matched_notification and parsed_action != ACTION_NONE:
        _apply_action(matched_notification, parsed_action)

    return JsonResponse({"detail": "ok", "incoming_id": incoming.id})


# Bloco: Extracao de mensagem do payload
def _extract_whatsapp_message(payload):
    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        message = value.get("messages", [])[0]
        phone_from = message.get("from", "")
        text_body = message.get("text", {}).get("body", "")
        return phone_from, text_body
    except (IndexError, AttributeError):
        return "", ""


# Bloco: Interpretacao da acao
def _parse_action(text_body: str):
    if not text_body:
        return ACTION_NONE
    text = text_body.strip()
    if text.startswith("1"):
        return ACTION_CONFIRMED
    if text.startswith("2"):
        return ACTION_DELAYED
    if text.startswith("3"):
        return ACTION_CANCELED
    return ACTION_NONE


# Bloco: Matching da notificacao
def _match_notification(phone_from: str, text_body: str):
    if not phone_from and not text_body:
        return None

    match = re.search(r"N(\\d+)", text_body.upper())
    if match:
        notification_id = int(match.group(1))
        notification = NotificationQueue.objects.filter(id=notification_id).first()
        if notification and (not notification.to_phone or notification.to_phone == phone_from):
            return notification
        return None

    if phone_from:
        since = timezone.now() - timedelta(hours=24)
        return (
            NotificationQueue.objects.filter(
                channel=CHANNEL_WHATSAPP,
                to_phone=phone_from,
                status=NOTIF_SENT,
                action_taken=ACTION_NONE,
                created_at__gte=since,
            )
            .order_by("-created_at")
            .first()
        )

    return None


# Bloco: Aplicacao da acao e resposta
def _apply_action(notification: NotificationQueue, action: str):
    notification.action_taken = action
    notification.save(update_fields=["action_taken"])

    if action == ACTION_CONFIRMED:
        _reply_whatsapp(notification.to_phone, "Confirmado ✅")
        return

    if action == ACTION_DELAYED:
        delayed_for = timezone.now() + timedelta(minutes=10)
        NotificationQueue.objects.create(
            user=notification.user,
            channel=notification.channel,
            title=notification.title,
            message=notification.message,
            scheduled_for=delayed_for,
            status=NOTIF_PENDING,
            to_phone=notification.to_phone,
        )
        _reply_whatsapp(notification.to_phone, "Adiado por 10 minutos ⏳")
        return

    if action == ACTION_CANCELED:
        _reply_whatsapp(notification.to_phone, "Cancelado 🧯")


# Bloco: Envio de resposta via WhatsApp
def _reply_whatsapp(phone: str, body: str):
    if not phone:
        return
    try:
        send_whatsapp_message_raw(phone, body)
    except Exception:
        return
