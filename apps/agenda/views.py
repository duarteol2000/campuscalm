from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from agenda.models import CalendarEvent, ReminderRule
from agenda.serializers import CalendarEventSerializer, ReminderRuleSerializer
from notifications.models import NotificationQueue
from planner.models import Task
from utils.constants import (
    CHANNEL_EMAIL,
    FEATURE_AGENDA_BASIC,
    FEATURE_IN_APP_REMINDERS,
    NOTIF_PENDING,
    REMINDER_TARGET_EVENT,
    REMINDER_TARGET_TASK,
)
from utils.features import require_feature
from utils.gating import gate_generate_reminders


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        require_feature(request.user, FEATURE_AGENDA_BASIC)
        return super().initial(request, *args, **kwargs)

    def get_queryset(self):
        return CalendarEvent.objects.filter(user=self.request.user).order_by("start_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReminderRuleViewSet(viewsets.ModelViewSet):
    serializer_class = ReminderRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        require_feature(request.user, FEATURE_IN_APP_REMINDERS)
        return super().initial(request, *args, **kwargs)

    def get_queryset(self):
        return ReminderRule.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AgendaWeekView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        require_feature(request.user, FEATURE_AGENDA_BASIC)
        now = timezone.now()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        events = CalendarEvent.objects.filter(
            user=request.user,
            start_at__date__gte=start_of_week.date(),
            start_at__date__lte=end_of_week.date(),
        ).order_by("start_at")
        return Response(CalendarEventSerializer(events, many=True).data)


class GenerateRemindersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        require_feature(request.user, FEATURE_IN_APP_REMINDERS)
        allowed, message = gate_generate_reminders(request.user)
        if not allowed:
            return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        created = 0
        rules = ReminderRule.objects.filter(user=request.user, is_active=True)
        for rule in rules:
            channels = rule.channels or [CHANNEL_EMAIL]
            if rule.target_type == REMINDER_TARGET_EVENT:
                events = CalendarEvent.objects.filter(user=request.user, start_at__gte=now)
                for event in events:
                    scheduled_for = event.start_at - timedelta(minutes=rule.remind_before_minutes)
                    if scheduled_for < now:
                        scheduled_for = now
                    for channel in channels:
                        title = f"Lembrete: {event.title}"
                        exists = NotificationQueue.objects.filter(
                            user=request.user,
                            channel=channel,
                            title=title,
                            scheduled_for=scheduled_for,
                        ).exists()
                        if not exists:
                            NotificationQueue.objects.create(
                                user=request.user,
                                channel=channel,
                                title=title,
                                message=f"Evento {event.title} em {event.start_at}.",
                                scheduled_for=scheduled_for,
                                status=NOTIF_PENDING,
                            )
                            created += 1
            if rule.target_type == REMINDER_TARGET_TASK:
                tasks = Task.objects.filter(user=request.user, due_date__gte=timezone.localdate())
                for task in tasks:
                    due_datetime = datetime.combine(task.due_date, time(9, 0), tzinfo=timezone.get_current_timezone())
                    scheduled_for = due_datetime - timedelta(minutes=rule.remind_before_minutes)
                    if scheduled_for < now:
                        scheduled_for = now
                    for channel in channels:
                        title = f"Lembrete: {task.title}"
                        exists = NotificationQueue.objects.filter(
                            user=request.user,
                            channel=channel,
                            title=title,
                            scheduled_for=scheduled_for,
                        ).exists()
                        if not exists:
                            NotificationQueue.objects.create(
                                user=request.user,
                                channel=channel,
                                title=title,
                                message=f"Tarefa {task.title} vence em {task.due_date}.",
                                scheduled_for=scheduled_for,
                                status=NOTIF_PENDING,
                            )
                            created += 1
        return Response({"created": created})
