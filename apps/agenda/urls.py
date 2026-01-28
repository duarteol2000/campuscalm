from django.urls import path
from rest_framework.routers import DefaultRouter

from agenda.views import CalendarEventViewSet, GenerateRemindersView, AgendaWeekView, ReminderRuleViewSet

router = DefaultRouter()
router.register(r"events", CalendarEventViewSet, basename="events")
router.register(r"reminder-rules", ReminderRuleViewSet, basename="reminder-rules")

urlpatterns = router.urls + [
    path("week/", AgendaWeekView.as_view(), name="agenda-week"),
    path("generate-reminders/", GenerateRemindersView.as_view(), name="agenda-generate-reminders"),
]
