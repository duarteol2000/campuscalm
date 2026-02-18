from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def _seconds_until_end_of_day(now: datetime) -> int:
    local_now = timezone.localtime(now)
    next_day = (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((next_day - local_now).total_seconds()), 60)


def maybe_send_absence_email(user, dashboard_url: str, now: datetime | None = None) -> bool:
    if not user or not user.is_active or not user.email:
        return False

    current_time = now or timezone.now()
    date_key = timezone.localdate(current_time).strftime("%Y%m%d")
    cache_key = f"campuscalm_absence_email:{user.id}:{date_key}"

    if cache.get(cache_key):
        return False

    subject = "CampusCalm: sentimos sua falta 🌿"
    body = (
        f"Oi, {user.name or user.email}.\n"
        "Percebemos alguns dias sem atividade.\n"
        "Que tal abrir o painel hoje e fazer um check-in rapido? Um passo pequeno ja ajuda.\n"
        f"(Acesse: {dashboard_url})"
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=False,
    )

    cache.set(cache_key, True, timeout=_seconds_until_end_of_day(current_time))
    logger.info("absence_email_sent user_id=%s", user.id)
    return True
