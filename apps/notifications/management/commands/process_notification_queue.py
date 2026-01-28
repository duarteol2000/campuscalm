from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone

from notifications.models import NotificationQueue
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
                if notification.channel == CHANNEL_EMAIL:
                    send_mail(notification.title, notification.message, None, [notification.user.email])
                elif notification.channel in {CHANNEL_WHATSAPP, CHANNEL_SMS, CHANNEL_IN_APP}:
                    # Mock para MVP.
                    pass
                notification.status = NOTIF_SENT
                notification.save()
                self.stdout.write(self.style.SUCCESS(f"Enviado: {notification.id}"))
            except Exception:
                notification.status = NOTIF_FAILED
                notification.save()
                self.stdout.write(self.style.ERROR(f"Falhou: {notification.id}"))
