from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional

from django.core.mail import send_mail
from django.utils import timezone

from notifications.models import NotificationQueue
from utils.constants import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    FEATURE_EMAIL_NOTIFICATIONS,
    FEATURE_SMS,
    FEATURE_WHATSAPP,
    NOTIF_FAILED,
    NOTIF_SENT,
)
from utils.features import has_feature


MESSAGE_REMINDER = "REMINDER"
MESSAGE_CARE = "CARE"
MESSAGE_INCENTIVE = "INCENTIVE"
MESSAGE_WARNING = "WARNING"
MESSAGE_ACHIEVEMENT = "ACHIEVEMENT"
MESSAGE_SYSTEM = "SYSTEM"

PRIORITY_LOW = "LOW"
PRIORITY_NORMAL = "NORMAL"
PRIORITY_HIGH = "HIGH"


@dataclass
class MessageTemplate:
    title: str
    body: str
    suggested_action: Optional[str] = None
    priority: str = PRIORITY_NORMAL


TEMPLATES = {
    (MESSAGE_INCENTIVE, "assessment_progress_up"): MessageTemplate(
        title="Progresso em disciplina",
        body=(
            "Voce avancou bem na disciplina {course}. "
            "Seu progresso atual esta em {progress}% e segue em evolução."
        ),
        suggested_action="Manter pequenos blocos de estudo pode ajudar a seguir tranquilo.",
        priority=PRIORITY_NORMAL,
    ),
    (MESSAGE_CARE, "assessment_progress_down"): MessageTemplate(
        title="Ajuste de ritmo",
        body=(
            "Seu progresso em {course} teve uma pequena queda. "
            "Isso pode acontecer em semanas mais intensas."
        ),
        suggested_action="Revisar pontos-chave com calma pode trazer mais estabilidade.",
        priority=PRIORITY_NORMAL,
    ),
    (MESSAGE_WARNING, "low_progress_upcoming"): MessageTemplate(
        title="Atenção suave",
        body=(
            "Talvez revisar {course} com pequenos blocos ajuda a reduzir a pressão desta semana."
        ),
        suggested_action="Escolha um horario curto para revisar o conteudo mais importante.",
        priority=PRIORITY_HIGH,
    ),
    (MESSAGE_ACHIEVEMENT, "course_passed"): MessageTemplate(
        title="Meta alcançada",
        body=(
            "Voce atingiu a media necessaria em {course}. Otimo avanco."
        ),
        suggested_action="Continue acompanhando as proximas avaliacões com tranquilidade.",
        priority=PRIORITY_NORMAL,
    ),
    (MESSAGE_ACHIEVEMENT, "semester_all_passed"): MessageTemplate(
        title="Semestre concluido",
        body=(
            "Voce concluiu o semestre com todas as disciplinas aprovadas. "
            "Parabens pelo cuidado e consistencia."
        ),
        suggested_action="Reserve um tempo para celebrar e recarregar as energias.",
        priority=PRIORITY_NORMAL,
    ),
    (MESSAGE_CARE, "semester_with_fail"): MessageTemplate(
        title="Continuidade do semestre",
        body=(
            "Algumas disciplinas ficaram abaixo da media no fechamento. "
            "Isso não diminui seu esforco, siga firme."
        ),
        suggested_action="Podemos organizar um plano simples de retomada para o proximo ciclo.",
        priority=PRIORITY_NORMAL,
    ),
    (MESSAGE_INCENTIVE, "semester_continue"): MessageTemplate(
        title="Plano de continuidade",
        body=(
            "Com alguns ajustes, voce pode recuperar o ritmo nas proximas semanas."
        ),
        suggested_action="Defina metas curtas e realistas para reequilibrar as disciplinas.",
        priority=PRIORITY_LOW,
    ),
}


def _build_message(message_type: str, context: dict) -> MessageTemplate:
    event = context.get("event")
    template = TEMPLATES.get((message_type, event))
    if not template:
        template = MessageTemplate(
            title="Mensagem do Campus Calm",
            body=context.get("body", "Estamos aqui para apoiar sua jornada academica."),
            suggested_action=context.get("suggested_action"),
        )
    return MessageTemplate(
        title=template.title.format(**context),
        body=template.body.format(**context),
        suggested_action=template.suggested_action.format(**context)
        if template.suggested_action
        else None,
        priority=template.priority,
    )


def _should_skip_duplicate(user, title: str) -> bool:
    since = timezone.now() - timedelta(hours=24)
    return NotificationQueue.objects.filter(user=user, title=title, scheduled_for__gte=since).exists()


def send_message(user, message_type: str, context: dict, channels: Optional[Iterable[str]] = None) -> None:
    if channels is None:
        channels = [CHANNEL_IN_APP]
    channels = list(dict.fromkeys(channels))
    if CHANNEL_IN_APP not in channels:
        channels.insert(0, CHANNEL_IN_APP)

    message = _build_message(message_type, context)
    if _should_skip_duplicate(user, message.title):
        return

    base_body = message.body
    if message.suggested_action:
        base_body = f"{base_body}\n\nSugestao: {message.suggested_action}"

    now = timezone.now()
    for channel in channels:
        if channel == CHANNEL_EMAIL and not has_feature(user, FEATURE_EMAIL_NOTIFICATIONS):
            continue
        if channel == CHANNEL_WHATSAPP and not has_feature(user, FEATURE_WHATSAPP):
            continue
        if channel == CHANNEL_SMS and not has_feature(user, FEATURE_SMS):
            continue

        status = NOTIF_SENT
        if channel == CHANNEL_EMAIL:
            try:
                send_mail(message.title, base_body, None, [user.email])
            except Exception:
                status = NOTIF_FAILED

        NotificationQueue.objects.create(
            user=user,
            channel=channel,
            title=message.title,
            message=base_body,
            scheduled_for=now,
            status=status,
        )
