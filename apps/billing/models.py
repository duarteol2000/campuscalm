from django.conf import settings
from django.db import models
from django.utils import timezone

from utils.constants import PLAN_CHOICES, PLAN_LITE


class Plan(models.Model):
    # Bloco: Dados do plano SaaS (compatível com contrato legado existente)
    code = models.CharField(max_length=10, choices=PLAN_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list)
    # CAMPUSCALM SAAS: preço e capacidade (0 = ilimitado)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_students = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def active(self):
        # Mantém compatibilidade sem quebrar código legado que já usa is_active.
        return self.is_active

    @active.setter
    def active(self, value):
        self.is_active = bool(value)

    def __str__(self):
        return f"{self.code}"

    @staticmethod
    def default_lite_features():
        return [
            "MOOD_BASIC",
            "POMODORO_BASIC",
            "PLANNER_BASIC",
            "AGENDA_BASIC",
            "IN_APP_REMINDERS",
            "DASHBOARD_BASIC",
            "CONTENT_LIMITED",
        ]

    @staticmethod
    def default_pro_features():
        return Plan.default_lite_features() + [
            "EMAIL_NOTIFICATIONS",
            "REPORTS_ADVANCED",
            "SEMESTER_SUMMARY",
            "COACH_ADVANCED",
            "CONTENT_FULL",
        ]


class UserSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.code if self.plan else PLAN_LITE}"


class Institution(models.Model):
    # Bloco: Entidade institucional (multi-tenant)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=20, blank=True)
    institution_code = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    website_url = models.URLField(blank=True)
    endereco = models.TextField(blank=True)
    cidade = models.CharField(max_length=120, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to="institution_logos/", blank=True, null=True)
    ativa = models.BooleanField(default=True)
    is_pilot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome_fantasia or self.razao_social


class InstitutionSubscription(models.Model):
    # Bloco: Assinatura institucional e validação de acesso
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Ativa"),
        (STATUS_SUSPENDED, "Suspensa"),
        (STATUS_CANCELED, "Cancelada"),
        (STATUS_EXPIRED, "Expirada"),
    ]

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="institution_subscriptions")
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_trial = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_date", "-id")

    def __str__(self):
        return f"{self.institution} | {self.plan.name} ({self.status})"

    @property
    def is_permanent(self):
        # Proposta de plano piloto/temporário: quando não existe data fim, permite acesso contínuo.
        return self.end_date is None
