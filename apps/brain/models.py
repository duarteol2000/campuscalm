from django.conf import settings
from django.db import models


class CategoriaEmocional(models.Model):
    nome = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=10)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class GatilhoEmocional(models.Model):
    categoria = models.ForeignKey(CategoriaEmocional, on_delete=models.CASCADE, related_name="gatilhos")
    palavras_chave = models.TextField()
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.categoria.slug} - gatilho"


class RespostaEmocional(models.Model):
    categoria = models.ForeignKey(CategoriaEmocional, on_delete=models.CASCADE, related_name="respostas")
    texto = models.TextField()
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.categoria.slug} - resposta"


class MicroIntervencao(models.Model):
    nome = models.CharField(max_length=120)
    texto = models.TextField()
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class InteracaoAluno(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interacoes_brain")
    mensagem_usuario = models.TextField()
    categoria_detectada = models.ForeignKey(
        CategoriaEmocional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interacoes",
    )
    resposta_texto = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(max_length=40, default="widget")

    def __str__(self):
        return f"{self.user_id} - {self.created_at:%Y-%m-%d %H:%M:%S}"


# Bloco: Estado de acao pendente no chat (concierge)
class ChatPendingAction(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="brain_pending_action",
    )
    pending_action = models.CharField(max_length=40)
    step = models.PositiveSmallIntegerField(default=1)
    draft_title = models.CharField(max_length=200, blank=True)
    draft_description = models.TextField(blank=True)
    draft_due_date = models.DateField(null=True, blank=True)
    draft_due_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} - {self.pending_action} - step {self.step}"


class WeeklyCoachingAssessment(models.Model):
    RISK_STABLE = "STABLE"
    RISK_LOW = "LOW"
    RISK_MODERATE = "MODERATE"
    RISK_HIGH = "HIGH"
    RISK_LEVEL_CHOICES = [
        (RISK_STABLE, "Stable"),
        (RISK_LOW, "Low"),
        (RISK_MODERATE, "Moderate"),
        (RISK_HIGH, "High"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_coaching_assessments")
    week_reference = models.DateField(help_text="Segunda-feira da semana avaliada")
    score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default=RISK_STABLE)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_reference"],
                name="uniq_weekly_coaching_user_week",
            )
        ]
        ordering = ("-week_reference", "-created_at")

    def __str__(self):
        return f"{self.user_id} - {self.week_reference} - {self.risk_level} ({self.score})"
