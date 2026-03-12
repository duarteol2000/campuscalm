from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_COORDINATOR = "coordinator"
    ROLE_PARENT = "parent"
    ROLE_INSTITUTION_ADMIN = "institution_admin"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Aluno"),
        (ROLE_TEACHER, "Professor"),
        (ROLE_COORDINATOR, "Coordenador"),
        (ROLE_PARENT, "Responsável"),
        (ROLE_INSTITUTION_ADMIN, "Admin Institucional"),
    ]

    LANGUAGE_PT_BR = "pt-BR"
    LANGUAGE_EN = "en"
    LANGUAGE_ES = "es"
    PREFERRED_LANGUAGE_CHOICES = [
        (LANGUAGE_PT_BR, "Português (Brasil)"),
        (LANGUAGE_EN, "English"),
        (LANGUAGE_ES, "Español"),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30, blank=True)
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    preferred_language = models.CharField(
        max_length=5,
        choices=PREFERRED_LANGUAGE_CHOICES,
        default=LANGUAGE_PT_BR,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

    def has_institutional_access(self):
        # Delega regra de acesso à camada de serviço institucional.
        from billing.services.institution_access import user_has_institutional_access

        return user_has_institutional_access(self)


# Bloco: Perfil e consentimentos do usuario
class UserProfile(models.Model):
    PLAN_FREE = "FREE"
    PLAN_PRO = "PRO"
    PLAN_PAID = "PAGO"  # legado
    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_PRO, "Pro"),
        (PLAN_PAID, "Pago (legado)"),
    ]
    GENDER_MALE = "M"
    GENDER_FEMALE = "F"
    GENDER_NON_BINARY = "N"
    GENDER_CHOICES = [
        (GENDER_MALE, "Masculino"),
        (GENDER_FEMALE, "Feminino"),
        (GENDER_NON_BINARY, "Nao binario"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default=PLAN_FREE)
    coach_enabled = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, default="")
    allow_whatsapp = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=False)
    allow_email = models.BooleanField(default=True)
    consent_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} profile"


# Bloco: Perfil acadêmico comportamental do aluno na instituição
class StudentProfile(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_GRADUATED = "graduated"
    STATUS_INACTIVE = "inactive"
    STATUS_TRANSFERRED = "transferred"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Ativo"),
        (STATUS_GRADUATED, "Formado"),
        (STATUS_INACTIVE, "Inativo"),
        (STATUS_TRANSFERRED, "Transferido"),
        (STATUS_SUSPENDED, "Suspenso"),
    ]

    ACCOUNT_INSTITUTIONAL = "institutional"
    ACCOUNT_PERSONAL = "personal"
    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_INSTITUTIONAL, "Institucional"),
        (ACCOUNT_PERSONAL, "Pessoal"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="student_profiles")
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="students",
    )
    enrollment_number = models.CharField(max_length=40, blank=True)
    grade_level = models.CharField(max_length=64, blank=True)
    class_group = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default=ACCOUNT_INSTITUTIONAL)
    graduated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("enrollment_number", "user__name")
        unique_together = ("user", "institution")

    def __str__(self):
        return f"{self.user.email} ({self.institution.institution_code})"

    def clean(self):
        if (
            self.user.institution_id
            and self.user.institution_id != self.institution_id
            and self.status == self.STATUS_ACTIVE
            and self.account_type == self.ACCOUNT_INSTITUTIONAL
        ):
            raise ValidationError("O usuario do aluno deve pertencer a mesma instituicao do perfil estudantil.")

    @property
    def is_active_for_institution(self):
        """
        Alunos ativos para dashboards institucionais:
        - status ativo
        - vínculo acadêmico institucional
        """
        return self.status == self.STATUS_ACTIVE and self.account_type == self.ACCOUNT_INSTITUTIONAL

    def activate_personal_mode(self):
        self.account_type = self.ACCOUNT_PERSONAL
        self.save(update_fields=["account_type", "updated_at"])

    def activate_institutional_mode(self):
        self.account_type = self.ACCOUNT_INSTITUTIONAL
        self.save(update_fields=["account_type", "updated_at"])

    def set_graduated(self, at=None):
        self.status = self.STATUS_GRADUATED
        self.graduated_at = at or timezone.now()
        self.save(update_fields=["status", "account_type", "graduated_at", "updated_at"])

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# Bloco: Vínculo de responsáveis por aluno
class ParentProfile(models.Model):
    RELATION_PARENT = "pai"
    RELATION_MOTHER = "mae"
    RELATION_RESPONSIBLE = "responsavel"
    RELATION_OTHER = "outro"
    RELATIONSHIP_CHOICES = [
        (RELATION_PARENT, "Pai"),
        (RELATION_MOTHER, "Mãe"),
        (RELATION_RESPONSIBLE, "Responsável"),
        (RELATION_OTHER, "Outro"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="children")
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.CASCADE, related_name="parent_links")
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default=RELATION_PARENT)
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="parent_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("relationship_type",)
        unique_together = (
            "user",
            "student",
            "institution",
            "relationship_type",
        )

    def __str__(self):
        return f"{self.user.email} -> {self.student.user.email} ({self.relationship_type})"

    def clean(self):
        if self.student.institution_id != self.institution_id:
            raise ValidationError("O aluno vinculado deve pertencer a mesma instituicao do relacionamento.")
        if self.user.institution_id and self.user.institution_id != self.institution_id:
            raise ValidationError("O responsavel deve pertencer a mesma instituicao do relacionamento.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
