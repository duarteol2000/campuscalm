from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from coach_ai.models import CoachLog
from semester.models import Assessment, Course, Semester
from utils.constants import COACH_REPROVACAO, COACH_SEMESTRE_CONCLUIDO, COURSE_FAILED, COURSE_PASSED

User = get_user_model()


class SemesterProgressTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="semester@example.com", name="Semestre", password="pass12345")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        self.semester = Semester.objects.create(
            user=self.user,
            name="2026.1",
            start_date=date.today(),
            end_date=date.today(),
        )
        self.course = Course.objects.create(semester=self.semester, title="Matematica")

    def test_course_progress_requires_assessment(self):
        response = self.client.get(f"/api/semester/courses/{self.course.id}/progress/")
        self.assertEqual(response.status_code, 403)
        self.assertIn("detail", response.data)

    def test_finish_semester_passed(self):
        Assessment.objects.create(course=self.course, title="Prova 1", score=Decimal("9"), max_score=Decimal("10"))
        response = self.client.post(f"/api/semester/finish/{self.semester.id}/")
        self.assertEqual(response.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, COURSE_PASSED)
        self.assertTrue(CoachLog.objects.filter(user=self.user, trigger_type=COACH_SEMESTRE_CONCLUIDO).exists())

    def test_finish_semester_failed(self):
        failing_course = Course.objects.create(semester=self.semester, title="Fisica", passing_grade=Decimal("7"))
        Assessment.objects.create(course=failing_course, title="Prova 1", score=Decimal("3"), max_score=Decimal("10"))
        response = self.client.post(f"/api/semester/finish/{self.semester.id}/")
        self.assertEqual(response.status_code, 200)
        failing_course.refresh_from_db()
        self.assertEqual(failing_course.status, COURSE_FAILED)
        self.assertTrue(CoachLog.objects.filter(user=self.user, trigger_type=COACH_REPROVACAO).exists())
