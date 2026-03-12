from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def _user_has_student_profile_in_institution(user, institution_id):
    from accounts.models import StudentProfile

    return StudentProfile.objects.filter(user=user, institution_id=institution_id).exists()


class StudyTask(models.Model):
    # Bloco: Tarefa de estudo com contexto de disciplina comportamental
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_tasks",
    )
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="study_tasks",
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date", "created_at")
        indexes = [
            models.Index(fields=["student", "institution", "due_date"]),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.title}"

    def clean(self):
        if not _user_has_student_profile_in_institution(self.student, self.institution_id):
            raise ValidationError("A tarefa deve estar vinculada a um aluno da mesma instituicao.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class StudySession(models.Model):
    # Bloco: Sessão de estudo para cálculo comportamental de consistência
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    subject = models.CharField(max_length=180)
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10000)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["student", "institution", "created_at"]),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.subject} ({self.duration_minutes}m)"

    def clean(self):
        if not _user_has_student_profile_in_institution(self.student, self.institution_id):
            raise ValidationError("A sessao deve estar vinculada a um aluno da mesma instituicao.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class EmotionalCheckin(models.Model):
    # Bloco: Indicador emocional para inteligência pedagógica
    mood = models.CharField(max_length=40)
    stress_level = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    motivation_level = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    notes = models.TextField(blank=True)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emotional_checkins",
    )
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="emotional_checkins",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["student", "institution", "created_at"]),
        ]

    def __str__(self):
        return f"{self.student_id} - mood:{self.mood}"

    def clean(self):
        if not _user_has_student_profile_in_institution(self.student, self.institution_id):
            raise ValidationError("O check-in deve estar vinculado a um aluno da mesma instituicao.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AcademicDisciplineScore(models.Model):
    # Bloco: Pontuação de disciplina acadêmica baseada em comportamento de estudo
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discipline_scores",
    )
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="discipline_scores",
    )
    score_value = models.PositiveIntegerField()
    classification = models.CharField(max_length=60)
    calculated_at = models.DateTimeField()

    class Meta:
        ordering = ("-calculated_at",)
        indexes = [
            models.Index(fields=["student", "institution", "calculated_at"]),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.score_value} ({self.classification})"

    def clean(self):
        if not _user_has_student_profile_in_institution(self.student, self.institution_id):
            raise ValidationError("O score deve estar vinculado a um aluno da mesma instituicao.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Achievement(models.Model):
    # Bloco: Gamificação para incentivar hábitos e consistência
    ACHIEVEMENT_CONSISTENCY_7_DAYS = "consistencia_7_dias"
    ACHIEVEMENT_TASKS_10 = "10_tarefas"
    ACHIEVEMENT_STUDY_30H = "30_horas_estudo"
    ACHIEVEMENT_SCORE_800 = "score_acima_800"
    TYPE_CHOICES = [
        (ACHIEVEMENT_CONSISTENCY_7_DAYS, "7 dias seguidos estudando"),
        (ACHIEVEMENT_TASKS_10, "10 tarefas concluídas"),
        (ACHIEVEMENT_STUDY_30H, "30 horas de estudo"),
        (ACHIEVEMENT_SCORE_800, "Score acima de 800"),
    ]

    student = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    institution = models.ForeignKey(
        "billing.Institution",
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    achievement_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    unlocked_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-unlocked_at",)
        unique_together = (
            "student",
            "institution",
            "achievement_type",
        )

    def __str__(self):
        return f"{self.student_id} - {self.achievement_type}"

    def clean(self):
        if not _user_has_student_profile_in_institution(self.student, self.institution_id):
            raise ValidationError("A conquista deve estar vinculada a um aluno da mesma instituicao.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
