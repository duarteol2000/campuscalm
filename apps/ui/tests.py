from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ParentProfile, StudentProfile, UserProfile
from billing.models import Institution, InstitutionSubscription, Plan
from utils.constants import FEATURE_DASHBOARD_BASIC, PLAN_PILOT

User = get_user_model()


class DashboardUiTests(TestCase):
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
            institution_code="UI001",
            slug="campuscalm-school-ui",
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
            email="ui-student@example.com",
            name="Student UI",
            password="pass12345",
            role=User.ROLE_STUDENT,
            institution=self.institution,
        )
        self.parent_user = User.objects.create_user(
            email="ui-parent@example.com",
            name="Parent UI",
            password="pass12345",
            role=User.ROLE_PARENT,
            institution=self.institution,
        )
        self.coord_user = User.objects.create_user(
            email="ui-coord@example.com",
            name="Coord UI",
            password="pass12345",
            role=User.ROLE_COORDINATOR,
            institution=self.institution,
        )

        UserProfile.objects.get_or_create(user=self.student_user)
        UserProfile.objects.get_or_create(user=self.parent_user)
        UserProfile.objects.get_or_create(user=self.coord_user)

        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            institution=self.institution,
            enrollment_number="UI-001",
            grade_level="1 ano",
            class_group="A",
        )
        ParentProfile.objects.create(
            user=self.parent_user,
            student=self.student_profile,
            relationship_type=ParentProfile.RELATION_RESPONSIBLE,
            institution=self.institution,
        )

    def test_parent_dashboard_ui_renders_parent_integration(self):
        self.client.force_login(self.parent_user)
        response = self.client.get(reverse("ui-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-dashboard-kind="parent"', html=False)
        self.assertContains(response, "/api/learning/dashboard/parent/")

    def test_institution_dashboard_ui_renders_institution_integration(self):
        self.client.force_login(self.coord_user)
        response = self.client.get(reverse("ui-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-dashboard-kind="teacher"', html=False)
        self.assertContains(response, 'data-dashboard-kind="institution"', html=False)
        self.assertContains(response, "/api/learning/dashboard/institution/")
