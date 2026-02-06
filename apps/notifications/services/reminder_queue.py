from datetime import datetime, time, timedelta

from django.utils import timezone

from accounts.models import UserProfile
from agenda.models import CalendarEvent, ReminderRule
from notifications.models import NotificationQueue
from planner.models import Task
from utils.constants import (
    CHANNEL_EMAIL,
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    NOTIF_PENDING,
    REMINDER_TARGET_EVENT,
    REMINDER_TARGET_TASK,
)


# Bloco: Preferencias do usuario
def _get_user_preferences(user):
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    return {
        "allow_email": getattr(profile, "allow_email", True),
        "allow_whatsapp": getattr(profile, "allow_whatsapp", True),
        "allow_sms": getattr(profile, "allow_sms", False),
        "phone": getattr(profile, "phone", "") or getattr(user, "phone_number", ""),
    }


# Bloco: Filtro de canais permitidos
def _filter_channels(channels, prefs):
    allowed = []
    for channel in channels:
        if channel == CHANNEL_EMAIL and prefs["allow_email"]:
            allowed.append(channel)
        if channel == CHANNEL_WHATSAPP and prefs["allow_whatsapp"]:
            allowed.append(channel)
        if channel == CHANNEL_SMS and prefs["allow_sms"]:
            allowed.append(channel)
    return allowed


# Bloco: Criacao de notificacao
def _queue_notification(user, channel, title, message, scheduled_for, phone=""):
    exists = NotificationQueue.objects.filter(
        user=user,
        channel=channel,
        title=title,
        scheduled_for=scheduled_for,
    ).exists()
    if exists:
        return False

    NotificationQueue.objects.create(
        user=user,
        channel=channel,
        title=title,
        message=message,
        scheduled_for=scheduled_for,
        status=NOTIF_PENDING,
        to_phone=phone or "",
    )
    return True


# Bloco: Lembretes para evento
def create_notifications_for_event(user, event: CalendarEvent) -> int:
    now = timezone.now()
    created = 0
    prefs = _get_user_preferences(user)
    rules = ReminderRule.objects.filter(user=user, is_active=True, target_type=REMINDER_TARGET_EVENT)
    for rule in rules:
        channels = rule.channels or [CHANNEL_EMAIL]
        allowed_channels = _filter_channels(channels, prefs)
        scheduled_for = event.start_at - timedelta(minutes=rule.remind_before_minutes)
        if scheduled_for < now:
            scheduled_for = now
        for channel in allowed_channels:
            title = f"Lembrete: {event.title}"
            message = f"Evento {event.title} em {event.start_at}."
            phone = prefs["phone"] if channel in {CHANNEL_WHATSAPP, CHANNEL_SMS} else ""
            if _queue_notification(user, channel, title, message, scheduled_for, phone):
                created += 1
    return created


# Bloco: Lembretes para tarefa
def create_notifications_for_task(user, task: Task) -> int:
    now = timezone.now()
    created = 0
    prefs = _get_user_preferences(user)
    rules = ReminderRule.objects.filter(user=user, is_active=True, target_type=REMINDER_TARGET_TASK)
    for rule in rules:
        channels = rule.channels or [CHANNEL_EMAIL]
        allowed_channels = _filter_channels(channels, prefs)
        due_datetime = datetime.combine(task.due_date, time(9, 0), tzinfo=timezone.get_current_timezone())
        scheduled_for = due_datetime - timedelta(minutes=rule.remind_before_minutes)
        if scheduled_for < now:
            scheduled_for = now
        for channel in allowed_channels:
            title = f"Lembrete: {task.title}"
            message = f"Tarefa {task.title} vence em {task.due_date}."
            phone = prefs["phone"] if channel in {CHANNEL_WHATSAPP, CHANNEL_SMS} else ""
            if _queue_notification(user, channel, title, message, scheduled_for, phone):
                created += 1
    return created


# Bloco: Lembretes para usuario (geracao completa)
def create_notifications_for_user(user) -> int:
    created = 0
    now = timezone.now()
    events = CalendarEvent.objects.filter(user=user, start_at__gte=now)
    for event in events:
        created += create_notifications_for_event(user, event)

    tasks = Task.objects.filter(user=user, due_date__gte=timezone.localdate())
    for task in tasks:
        created += create_notifications_for_task(user, task)

    return created
