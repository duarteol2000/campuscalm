from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import StudentProfile
from billing.models import Institution, InstitutionSubscription, Plan
from utils.constants import PLAN_PILOT

User = get_user_model()


class StudyAssistantApiTests(APITestCase):
    def setUp(self):
        self.plan, _ = Plan.objects.get_or_create(
            code=PLAN_PILOT,
            defaults={
                "name": "Piloto",
                "description": "Plano piloto",
                "price": 0,
                "max_students": 100,
                "is_active": True,
                "features": [],
            },
        )
        self.institution = Institution.objects.create(
            razao_social="Instituto CampusCalm",
            nome_fantasia="Instituto",
            institution_code="INST001",
            slug="instituto-campuscalm",
            ativa=True,
        )
        InstitutionSubscription.objects.create(
            institution=self.institution,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=30),
            end_date=timezone.localdate() + timedelta(days=180),
            status=InstitutionSubscription.STATUS_ACTIVE,
        )
        self.student = User.objects.create_user(
            email="aluno@example.com",
            name="Aluno",
            password="pass12345",
            role=User.ROLE_STUDENT,
            institution=self.institution,
            preferred_language=User.LANGUAGE_PT_BR,
        )
        StudentProfile.objects.create(
            user=self.student,
            institution=self.institution,
            enrollment_number="EN001",
            class_group="A",
        )
        self.teacher = User.objects.create_user(
            email="teacher2@example.com",
            name="Teacher",
            password="pass12345",
            role=User.ROLE_TEACHER,
            institution=self.institution,
        )

    def _authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_assistant_detects_subject_and_returns_guidance(self):
        self._authenticate(self.student)
        response = self.client.post(
            "/api/study-assistant/ask/",
            {"message": "nao to entendendo quimica"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subject"], "quimica")
        self.assertIn("25 minutos", response.data["message"])

    def test_assistant_respects_preferred_language(self):
        self.student.preferred_language = User.LANGUAGE_ES
        self.student.save(update_fields=["preferred_language"])
        self._authenticate(self.student)
        response = self.client.post(
            "/api/study-assistant/ask/",
            {"message": "como aprender biologia"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], User.LANGUAGE_ES)
        self.assertIn("rutina", response.data["message"])

    def test_assistant_handles_text_variations_and_typos(self):
        self._authenticate(self.student)
        response = self.client.post(
            "/api/study-assistant/ask/",
            {"message": "me ajuda em matematicaa"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subject"], "matematica")
        self.assertIn("rotina", response.data["message"].lower())

    def test_assistant_blocks_cross_institution_request(self):
        other_institution = Institution.objects.create(
            razao_social="Outra Instituicao",
            nome_fantasia="Outra",
            institution_code="INST002",
            slug="outra-instituicao",
            ativa=True,
        )
        InstitutionSubscription.objects.create(
            institution=other_institution,
            plan=self.plan,
            start_date=timezone.localdate() - timedelta(days=10),
            end_date=timezone.localdate() + timedelta(days=10),
            status=InstitutionSubscription.STATUS_ACTIVE,
        )
        self._authenticate(self.student)
        response = self.client.post(
            "/api/study-assistant/ask/",
            {"message": "como estudar fisica", "institution_id": other_institution.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_assistant_rejects_non_student_role(self):
        self._authenticate(self.teacher)
        response = self.client.post(
            "/api/study-assistant/ask/",
            {"message": "como estudar fisica"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
