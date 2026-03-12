from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import ParentProfile, StudentProfile
from billing.models import Institution, InstitutionSubscription, Plan
from learning.models import AcademicDisciplineScore, EmotionalCheckin, StudySession, StudyTask
from learning.services.discipline_score import calculate_student_score
from utils.constants import FEATURE_DASHBOARD_BASIC, PLAN_PILOT

User = get_user_model()


class LearningApiTests(APITestCase):
    def setUp(self):
        self.plan, _ = Plan.objects.get_or_create(
            code=PLAN_PILOT,
            defaults={
                "name": "Piloto",
                "description": "Plano piloto",
                "price": 0,
                "max_students": 500,
                "is_active": True,
                "features": [FEATURE_DASHBOARD_BASIC],
            },
        )
        self.institution = Institution.objects.create(
            razao_social="CampusCalm Escola LTDA",
            nome_fantasia="CampusCalm School",
            institution_code="CCS001",
            slug="campuscalm-school",
            ativa=True,
            is_pilot=True,
        )
        InstitutionSubscription.objects.create(
            institution=self.institution,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=30),
            end_date=timezone.localdate() + timedelta(days=365),
            status=InstitutionSubscription.STATUS_ACTIVE,
            is_trial=True,
        )

        self.student_user = User.objects.create_user(
            email="student@example.com",
            name="Student",
            password="pass12345",
            role=User.ROLE_STUDENT,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        self.parent_user = User.objects.create_user(
            email="parent@example.com",
            name="Parent",
            password="pass12345",
            role=User.ROLE_PARENT,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        self.teacher_user = User.objects.create_user(
            email="teacher@example.com",
            name="Teacher",
            password="pass12345",
            role=User.ROLE_TEACHER,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        self.coord_user = User.objects.create_user(
            email="coord@example.com",
            name="Coordinator",
            password="pass12345",
            role=User.ROLE_COORDINATOR,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            name="Admin",
            password="pass12345",
            role=User.ROLE_INSTITUTION_ADMIN,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            institution=self.institution,
            enrollment_number="2026A1",
            grade_level="1 ano",
            class_group="A",
        )
        ParentProfile.objects.create(
            user=self.parent_user,
            student=self.student_profile,
            relationship_type=ParentProfile.RELATION_RESPONSIBLE,
            institution=self.institution,
        )

        for offset in range(3):
            StudySession.objects.create(
                student=self.student_user,
                institution=self.institution,
                subject="Matematica",
                duration_minutes=60,
                notes=f"Session {offset}",
            )
        StudyTask.objects.create(
            student=self.student_user,
            institution=self.institution,
            title="Lista 1",
            due_date=timezone.localdate() + timedelta(days=2),
            completed=False,
        )
        EmotionalCheckin.objects.create(
            student=self.student_user,
            institution=self.institution,
            mood="ok",
            stress_level=4,
            motivation_level=8,
            notes="Tudo sob controle",
        )
        AcademicDisciplineScore.objects.create(
            student=self.student_user,
            institution=self.institution,
            score_value=720,
            classification="disciplinado",
            calculated_at=timezone.now(),
        )
        self.other_institution = Institution.objects.create(
            razao_social="Outra Escola LTDA",
            nome_fantasia="Outra Escola",
            institution_code="CCS002",
            slug="outra-escola",
            ativa=True,
        )
        InstitutionSubscription.objects.create(
            institution=self.other_institution,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=10),
            end_date=timezone.localdate() + timedelta(days=60),
            status=InstitutionSubscription.STATUS_ACTIVE,
        )
        self.other_student = User.objects.create_user(
            email="other-student@example.com",
            name="Other Student",
            password="pass12345",
            role=User.ROLE_STUDENT,
            institution=self.other_institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        StudentProfile.objects.create(
            user=self.other_student,
            institution=self.other_institution,
            enrollment_number="2026B1",
            grade_level="2 ano",
            class_group="B",
        )
        AcademicDisciplineScore.objects.create(
            student=self.other_student,
            institution=self.other_institution,
            score_value=900,
            classification="mestre da consistencia",
            calculated_at=timezone.now(),
        )

    def _authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def _create_same_institution_student(self, email, name, enrollment_number, class_group="A", score_value=650):
        user = User.objects.create_user(
            email=email,
            name=name,
            password="pass12345",
            role=User.ROLE_STUDENT,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        StudentProfile.objects.create(
            user=user,
            institution=self.institution,
            enrollment_number=enrollment_number,
            grade_level="1 ano",
            class_group=class_group,
        )
        AcademicDisciplineScore.objects.create(
            student=user,
            institution=self.institution,
            score_value=score_value,
            classification="organizado",
            calculated_at=timezone.now(),
        )
        return user

    def test_score_service_returns_clamped_score(self):
        score = calculate_student_score(self.student_user, institution_id=self.institution.id, at=timezone.now())
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1000)

    def test_learning_models_reject_institution_mismatch(self):
        with self.assertRaises(ValidationError):
            StudyTask.objects.create(
                student=self.student_user,
                institution=self.other_institution,
                title="Invalida",
                due_date=timezone.localdate(),
            )

    def test_student_dashboard_api_returns_student_data(self):
        self._authenticate(self.student_user)
        response = self.client.get("/api/learning/dashboard/student/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["score_current"]["score_value"], 720)
        self.assertIn("tasks_pending", response.data)

    def test_parent_dashboard_only_returns_linked_child(self):
        self._authenticate(self.parent_user)
        response = self.client.get("/api/learning/dashboard/parent/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["children"]), 1)
        self.assertEqual(response.data["children"][0]["student_name"], self.student_user.name)

    def test_teacher_dashboard_requires_teacher_role(self):
        self._authenticate(self.student_user)
        response = self.client.get("/api/learning/dashboard/teacher/")
        self.assertEqual(response.status_code, 403)

    def test_teacher_dashboard_returns_risk_and_ranking(self):
        self._authenticate(self.teacher_user)
        response = self.client.get("/api/learning/dashboard/teacher/?class_group=A")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ranking", response.data)
        self.assertIn("pedagogical_insights", response.data)
        self.assertEqual(response.data["ranking"][0]["student_name"], self.student_user.name)

    def test_institution_dashboard_requires_coord_or_admin(self):
        self._authenticate(self.coord_user)
        response = self.client.get("/api/learning/dashboard/institution/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("institution_average", response.data)

    def test_teacher_dashboard_enforces_institution_isolation(self):
        self._authenticate(self.teacher_user)
        response = self.client.get(f"/api/learning/dashboard/teacher/?institution_id={self.other_institution.id}")
        self.assertEqual(response.status_code, 403)

    def test_teacher_dashboard_excludes_other_institutions_from_ranking(self):
        self._authenticate(self.teacher_user)
        response = self.client.get("/api/learning/dashboard/teacher/")
        self.assertEqual(response.status_code, 200)
        ranking_names = {item["student_name"] for item in response.data["ranking"]}
        self.assertIn(self.student_user.name, ranking_names)
        self.assertNotIn(self.other_student.name, ranking_names)

    def test_institution_dashboard_excludes_other_institution_students(self):
        self._authenticate(self.coord_user)
        response = self.client.get("/api/learning/dashboard/institution/")
        self.assertEqual(response.status_code, 200)
        top_names = {item["student_name"] for item in response.data["top_students"]}
        self.assertIn(self.student_user.name, top_names)
        self.assertNotIn(self.other_student.name, top_names)

    def test_expired_institution_subscription_blocks_dashboard_access(self):
        InstitutionSubscription.objects.filter(institution=self.institution).update(
            end_date=timezone.localdate() - timedelta(days=1)
        )
        self._authenticate(self.student_user)
        response = self.client.get("/api/learning/dashboard/student/")
        self.assertEqual(response.status_code, 403)

    def test_ranking_is_only_available_for_institution_staff_roles(self):
        self._authenticate(self.teacher_user)
        teacher_response = self.client.get("/api/learning/dashboard/teacher/")
        self.assertEqual(teacher_response.status_code, 200)
        self.assertTrue(isinstance(teacher_response.data["ranking"], list))

        self.client.credentials()
        self._authenticate(self.student_user)
        student_response = self.client.get("/api/learning/dashboard/student/")
        self.assertEqual(student_response.status_code, 200)
        self.assertNotIn("ranking", student_response.data)

        self.client.credentials()
        self._authenticate(self.parent_user)
        parent_response = self.client.get("/api/learning/dashboard/parent/")
        self.assertEqual(parent_response.status_code, 200)
        self.assertNotIn("ranking", parent_response.data)

    def test_teacher_dashboard_filters_ranking_by_student_name(self):
        self._create_same_institution_student(
            email="maria@example.com",
            name="Maria Silva",
            enrollment_number="2026A2",
            score_value=810,
        )
        self._authenticate(self.teacher_user)
        response = self.client.get("/api/learning/dashboard/teacher/?search=Maria")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["ranking"]), 1)
        self.assertEqual(response.data["ranking"][0]["student_name"], "Maria Silva")
        self.assertEqual(response.data["ranking_filters"]["search"], "Maria")

    def test_teacher_dashboard_paginates_ranking(self):
        self._create_same_institution_student(
            email="ana@example.com",
            name="Ana Costa",
            enrollment_number="2026A3",
            score_value=805,
        )
        self._create_same_institution_student(
            email="bruno@example.com",
            name="Bruno Lima",
            enrollment_number="2026A4",
            score_value=790,
        )
        self._authenticate(self.teacher_user)
        response = self.client.get("/api/learning/dashboard/teacher/?page=2&page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["ranking"]), 1)
        self.assertEqual(response.data["ranking_pagination"]["page"], 2)
        self.assertEqual(response.data["ranking_pagination"]["page_size"], 1)
        self.assertEqual(response.data["ranking_pagination"]["total_pages"], 3)
        self.assertTrue(response.data["ranking_pagination"]["has_previous"])

    def test_openapi_schema_endpoint_is_available(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/learning/dashboard/student/", response.content.decode())
        self.assertIn("/api/study-assistant/ask/", response.content.decode())

    def test_openapi_export_file_exists_for_external_delivery(self):
        export_path = Path(settings.BASE_DIR) / "docs" / "openapi-campuscalm.yaml"
        self.assertTrue(export_path.exists())
