from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User, UserProfile
from brain.models import WeeklyCoachingAssessment
from brain.services.coaching_service import calculate_weekly_score
from mood.models import MoodEntry
from planner.models import Task
from semester.models import Semester, SemesterCheckin
from utils.constants import MOOD_VERY_BAD, TASK_TODO


class WeeklyCoachingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="coach@example.com",
            name="Coach User",
            password="pass12345",
        )
        self.profile = self.user.profile

    def test_calculate_weekly_score_returns_high_when_all_risk_conditions_match(self):
        today = timezone.localdate()
        old_timestamp = timezone.now() - timedelta(days=4)

        for idx in range(2):
            task = Task.objects.create(
                user=self.user,
                title=f"atrasada-{idx}",
                description="",
                due_date=today - timedelta(days=1),
                stress_level=3,
                status=TASK_TODO,
            )
            Task.objects.filter(pk=task.pk).update(created_at=old_timestamp)

        mood = MoodEntry.objects.create(user=self.user, mood=MOOD_VERY_BAD, notes="")
        MoodEntry.objects.filter(pk=mood.pk).update(created_at=old_timestamp)

        semester = Semester.objects.create(
            user=self.user,
            name="2026.1",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=90),
        )
        checkin = SemesterCheckin.objects.create(semester=semester, overall_stress=5, comment="")
        SemesterCheckin.objects.filter(pk=checkin.pk).update(created_at=old_timestamp)

        result = calculate_weekly_score(self.user)

        self.assertEqual(result.score, 100)
        self.assertEqual(result.risk_level, WeeklyCoachingAssessment.RISK_HIGH)
        self.assertGreaterEqual(result.metrics["days_without_activity"], 3)
        self.assertGreaterEqual(result.metrics["overdue_tasks"], 2)
        self.assertLess(result.metrics["mood_average_0_10"], 5)
        self.assertGreater(result.metrics["stress_average_0_10"], 7)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_run_weekly_coaching_creates_assessment_and_does_not_resend_same_week(self):
        self.profile.coach_enabled = True
        self.profile.save(update_fields=["coach_enabled"])

        today = timezone.localdate()
        old_timestamp = timezone.now() - timedelta(days=4)
        for idx in range(2):
            task = Task.objects.create(
                user=self.user,
                title=f"atrasada-cmd-{idx}",
                description="",
                due_date=today - timedelta(days=1),
                stress_level=2,
                status=TASK_TODO,
            )
            Task.objects.filter(pk=task.pk).update(created_at=old_timestamp)

        call_command("run_weekly_coaching", "--user-email", self.user.email)

        assessments = WeeklyCoachingAssessment.objects.filter(user=self.user)
        self.assertEqual(assessments.count(), 1)
        assessment = assessments.first()
        self.assertEqual(assessment.risk_level, WeeklyCoachingAssessment.RISK_LOW)
        self.assertTrue(assessment.email_sent)
        self.assertEqual(len(mail.outbox), 1)

        call_command("run_weekly_coaching", "--user-email", self.user.email)

        self.assertEqual(WeeklyCoachingAssessment.objects.filter(user=self.user).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
