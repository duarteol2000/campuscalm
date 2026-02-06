from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import UserProfile
from notifications.models import NotificationQueue
from notifications.services.whatsapp_service import normalize_phone, send_whatsapp_message_raw
from utils.constants import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    NOTIF_FAILED,
    NOTIF_PENDING,
    NOTIF_SENT,
)


class Command(BaseCommand):
    help = "Processa a fila de notificacoes pendentes."

    def handle(self, *args, **options):
        now = timezone.now()
        pending = NotificationQueue.objects.filter(status=NOTIF_PENDING, scheduled_for__lte=now)
        for notification in pending:
            try:
                # Bloco: Contagem de tentativas
                notification.attempts += 1

                if notification.channel == CHANNEL_EMAIL:
                    # Bloco: Envio de email
                    send_mail(notification.title, notification.message, None, [notification.user.email])
                elif notification.channel == CHANNEL_WHATSAPP:
                    # Bloco: Envio de WhatsApp
                    phone = notification.to_phone
                    if not phone:
                        try:
                            phone = notification.user.profile.phone
                        except UserProfile.DoesNotExist:
                            phone = notification.user.phone_number
                    phone = normalize_phone(phone)
                    if not phone:
                        raise RuntimeError("Telefone WhatsApp nao informado.")

                    body = f"{notification.message} [#N{notification.id}]\\nResponda 1 confirmar, 2 adiar 10min, 3 cancelar"
                    response = send_whatsapp_message_raw(phone, body)
                    provider_id = ""
                    if isinstance(response, dict):
                        provider_id = response.get("messages", [{}])[0].get("id", "")
                    if response is None:
                        raise RuntimeError("Falha no envio do WhatsApp.")
                    notification.provider = "META"
                    notification.provider_message_id = provider_id or ""
                    notification.to_phone = phone
                elif notification.channel == CHANNEL_SMS:
                    # Bloco: SMS mock (fallback)
                    notification.provider = "MOCK"
                elif notification.channel == CHANNEL_IN_APP:
                    # Bloco: In-app (sem envio externo)
                    notification.provider = "IN_APP"

                notification.status = NOTIF_SENT
                notification.sent_at = timezone.now()
                notification.last_error = ""
                notification.save()
                self.stdout.write(self.style.SUCCESS(f"Enviado: {notification.id}"))
            except Exception as exc:
                notification.status = NOTIF_FAILED
                notification.last_error = str(exc)
                notification.save()
                self.stdout.write(self.style.ERROR(f"Falhou: {notification.id}"))
