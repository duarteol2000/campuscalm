from semester.models import Assessment, Course, Semester
from agenda.models import ReminderRule
from onboarding.models import UserSetupProgress
from utils.constants import SEMESTER_ACTIVE


def refresh_user_progress(user):
    progress, _ = UserSetupProgress.objects.get_or_create(user=user)
    progress.has_profile = bool(user.name)
    progress.has_active_semester = Semester.objects.filter(user=user, status=SEMESTER_ACTIVE).exists()
    progress.has_at_least_one_course = Course.objects.filter(semester__user=user).exists()
    progress.has_at_least_one_assessment = Assessment.objects.filter(course__semester__user=user).exists()
    progress.has_reminder_rule = ReminderRule.objects.filter(user=user, is_active=True).exists()
    progress.save()
    return progress
