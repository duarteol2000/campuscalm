import re
import random
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import permissions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from agenda.models import CalendarEvent
from brain.constants import ANXIETY_KEYWORDS, CONTEXT_MESSAGES, EXAM_KEYWORDS
from brain.models import (
    CategoriaEmocional,
    ChatPendingAction,
    GatilhoEmocional,
    InteracaoAluno,
    MicroIntervencao,
    RespostaEmocional,
)
from notifications.models import InAppNotification
from planner.models import Task
from utils.constants import (
    EVENT_APRESENTACAO,
    EVENT_AULA_IMPORTANTE,
    EVENT_ENTREGA,
    EVENT_ESTUDAR_FACULDADE,
    EVENT_OUTRO,
    EVENT_PROVA,
    EVENT_REUNIAO_GRUPO,
    EVENT_REUNIAO_PROFESSORES,
    TASK_TODO,
)


class WidgetChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=300)


FALLBACK_REPLIES = [
    "Estou aqui com voce. Quer me contar um pouco mais sobre isso?",
    "Entendi. Me fala um pouco mais para eu poder te ajudar melhor.",
]
ENGLISH_FALLBACK_REPLIES = [
    "I'm here with you. Can you tell me a little more about this?",
    "Got it. Tell me a bit more so I can help you better.",
]
BLINDAGEM_REPLY = (
    "Vamos simplificar.\n"
    "Escolha o que mais se aproxima do que voce precisa agora:\n\n"
    "• Ansiedade\n"
    "• Organizacao\n"
    "• Estudos\n"
    "• Prazo"
)
BLINDAGEM_NEUTRAL_REPLY = "Vamos por partes: diga em uma palavra se e ansiedade, organizacao, estudos ou prazo."
BLINDAGEM_CATEGORY_MAP = {
    "ansiedade": "stress",
    "organizacao": "foco_alto",
    "estudos": "duvida",
    "prazo": "stress",
}

CATEGORY_PRIORITY = [
    "evolucao",
    "foco_alto",
    "social",
    "duvida",
    "motivacao_baixa",
    "cansaco_mental",
    "stress",
]

SOCIAL_STRONG_HINTS = ("obrigad", "valeu")
NEGATIVE_KEYWORDS = [
    "ansioso",
    "ansiosa",
    "ansiedade",
    "nervoso",
    "nervosa",
    "cansado",
    "cansada",
    "estressado",
    "estressada",
    "dificil",
    "difícil",
    "medo",
    "preocupado",
    "preocupada",
    "triste",
    "anxious",
    "anxiety",
    "nervous",
    "stressed",
    "overwhelmed",
    "afraid",
    "scared",
    "tired",
    "exhausted",
    "worried",
]
WEAK_POSITIVE_KEYWORDS = [
    "show",
    "top",
    "massa",
]
SHORT_DIRECTION_PATTERNS = (
    "o que faco",
    "oque faco",
    "oq faco",
    "q faco",
    "oq eu faco",
    "o que eu faco",
    "oq fazer",
    "que faco",
    "e agora",
    "me ajuda",
    "me ajuda pf",
    "me ajuda por favor",
    "socorro",
    "nao sei",
    "what should i do",
    "what do i do",
    "what do i do now",
    "now what",
    "help me",
    "i dont know",
    "i don't know",
    "what now",
)
GENERIC_QUESTION_PATTERNS = SHORT_DIRECTION_PATTERNS + (
    "o que eu faco",
    "o que eu faco agora",
    "oque eu faco",
    "o que fazer",
    "nao sei o que fazer",
)
TASK_CREATION_KEYWORDS = (
    "crie uma tarefa",
    "criar tarefa",
    "crie tarefa",
    "crie a tarefa",
    "crie a seguinte tarefa",
    "criasse a seguinte tarefa",
    "criasse a tarefa",
    "criasse tarefa",
    "preciso estudar",
    "me lembre",
    "lembra de",
    "anote",
    "coloca na minha lista",
)
TASK_TRIGGER_PREFIXES = (
    "quero criar uma tarefa para",
    "quero criar uma tarefa",
    "quero criar tarefa para",
    "quero criar tarefa",
    "crie uma tarefa para",
    "crie uma tarefa",
    "crie a seguinte tarefa para",
    "crie a seguinte tarefa",
    "crie a tarefa para",
    "crie a tarefa",
    "crie tarefa para",
    "crie tarefa",
    "criasse a seguinte tarefa para",
    "criasse a seguinte tarefa",
    "criasse a tarefa para",
    "criasse a tarefa",
    "criasse tarefa para",
    "criasse tarefa",
    "criar tarefa para",
    "criar tarefa",
    "preciso estudar",
    "me lembre de",
    "me lembre",
    "lembra de",
    "anote",
    "coloca na minha lista",
)
TASK_CREATION_ACTION_HINTS = (
    "crie",
    "criar",
    "criasse",
    "anote",
    "anotar",
    "adiciona",
    "adicionar",
    "coloca",
    "colocar",
)
TASK_GREETING_PREFIXES = (
    "bom dia",
    "boa tarde",
    "boa noite",
    "oi",
    "ola",
    "olá",
    "hello",
    "hi",
)
TASK_CONCIERGE_ACTION = "create_task"
TASK_CONCIERGE_EXPIRATION_MINUTES = 15
TASK_CONCIERGE_ASK_SCOPE = "📝 Criando nova tarefa (1/2)\nEntendi, voce quer criar uma tarefa.\nQual a descricao da tarefa?"
TASK_CONCIERGE_ASK_DUE = "📝 Criando nova tarefa (2/2)\nQual a data e hora de entrega?"
TASK_CONCIERGE_CONFIRM = "✅ Tarefa criada: {title}\n🗓 Prazo: {due_date}\n🔔 Veja em Tarefas"
TASK_CONCIERGE_RETRY_DUE = "Nao consegui entender a data/hora. Ex.: amanha 18h, hoje, 25/02 09:00, 25/02, sexta 14h."
TASK_CONCIERGE_CANCEL = "Tudo bem, cancelei a criacao da tarefa."
EVENT_CONCIERGE_ACTION = "create_event"
EVENT_CONCIERGE_ASK_SCOPE = "🗓 Criando novo evento (1/2)\nQual o compromisso na agenda?"
EVENT_CONCIERGE_ASK_WHEN = (
    "🗓 Criando novo evento (2/2)\n"
    "Perfeito. Qual o tipo do evento? (prova, entrega, aula, reuniao, outro)\n"
    "Agora me diga a data e hora.\n"
    "Ex.: prova amanha 14h | reuniao 25/02 09:00"
)
EVENT_CONCIERGE_CONFIRM = "✅ Evento criado: {title}\n🗓 Quando: {when}\n🔔 Veja em Agenda"
EVENT_CONCIERGE_RETRY_WHEN = (
    "Nao consegui entender. Informe tipo + data/hora. "
    "Ex.: prova amanha 14h, reuniao 25/02 09:00."
)
EVENT_CONCIERGE_ASK_ONLY_WHEN = "Perfeito, tipo salvo. Agora me diga apenas a data e hora. Ex.: amanha 14h | 25/02 09:00"
EVENT_CREATION_KEYWORDS = (
    "agenda",
    "agendar",
    "agende",
    "marcar",
    "marque",
    "marcasse",
    "colocar na agenda",
    "evento",
)
EVENT_COMMITMENT_KEYWORDS = (
    "reuniao",
    "prova",
    "consulta",
    "aula",
    "evento",
    "apresentacao",
    "seminario",
    "banca",
    "entrega",
    "compromisso",
)
EVENT_TRIGGER_PREFIXES = (
    "quero agendar",
    "agende para mim",
    "agende",
    "agendar",
    "marcar",
    "marque",
    "colocar na agenda",
    "coloque na agenda",
    "evento",
)
EVENT_GENERIC_REQUEST_PATTERNS = (
    "quero criar uma agenda",
    "quero criar agenda",
    "criar uma agenda",
    "criar agenda",
    "quero agendar",
    "agendar evento",
    "criar evento",
    "marcar evento",
)
TASK_CANCEL_KEYWORDS = ("cancelar", "deixa", "nao", "não", "parar")
TASK_URGENT_KEYWORDS = ("urgente", "desespero", "desesperado", "desesperada")
GREETING_REPLIES = {
    "bom dia": "Bom dia! Como posso te ajudar hoje?",
    "boa tarde": "Boa tarde! Como posso te ajudar hoje?",
    "boa noite": "Boa noite! Como posso te ajudar hoje?",
}
WEEKDAY_MAP = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}
PORTUGUESE_HOUR_WORDS = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "catorze": 14,
    "quatorze": 14,
    "quinze": 15,
    "dezesseis": 16,
    "dezessete": 17,
    "dezoito": 18,
    "dezenove": 19,
    "vinte": 20,
    "vinte e um": 21,
    "vinte e uma": 21,
    "vinte e dois": 22,
    "vinte e tres": 23,
}
PORTUGUESE_MINUTE_WORDS = {
    "quinze": 15,
    "trinta": 30,
    "meia": 30,
    "quarenta e cinco": 45,
}
PORTUGUESE_HOUR_WORDS_PATTERN = "|".join(
    sorted((re.escape(word) for word in PORTUGUESE_HOUR_WORDS.keys()), key=len, reverse=True)
)
PORTUGUESE_MINUTE_WORDS_PATTERN = "|".join(
    sorted((re.escape(word) for word in PORTUGUESE_MINUTE_WORDS.keys()), key=len, reverse=True)
)
SHORT_DIRECTION_CONTEXT_HINTS = (
    "medo",
    "ansiosa",
    "ansioso",
    "nervosa",
    "nervoso",
    "prova",
    "teste",
    "apresentacao",
    "nervous",
    "anxious",
    "scared",
    "afraid",
    "exam",
    "test",
    "presentation",
)
SHORT_DIRECTION_ENGLISH_HINTS = (
    "what",
    "help",
    "exam",
    "nervous",
)
SHORT_DIRECTION_POSITIVE_REPLIES = (
    "estou bem",
    "melhorou",
    "to bem",
    "tô bem",
    "ok",
    "certo",
    "obrigada",
    "valeu",
    "ajudou",
)
SHORT_DIRECTION_POSITIVE_REPLIES_EN = (
    "better",
    "ok",
    "thanks",
    "thank you",
    "it helped",
)
SHORT_DIRECTION_NEGATIVE_REPLIES = (
    "nao resolveu",
    "não resolveu",
    "nao ajudou",
    "não ajudou",
    "ainda estou nervosa",
    "ainda to nervosa",
    "ainda tô nervosa",
    "continuo nervosa",
    "ainda ansiosa",
    "to mal",
    "tô mal",
)
SHORT_DIRECTION_NEGATIVE_REPLIES_EN = (
    "still nervous",
    "didn't help",
    "didnt help",
    "still anxious",
)
EMOTIONAL_INTENT_KEYWORDS = (
    "ansioso",
    "ansiosa",
    "ansiedade",
    "triste",
    "estressado",
    "estressada",
    "cansado",
    "cansada",
    "preocupado",
    "preocupada",
    "anxious",
    "anxiety",
    "stressed",
    "sad",
    "worried",
    "tired",
)
TASK_INTENT_KEYWORDS = (
    "tarefa",
    "revisar",
    "estudar",
    "fazer",
    "ler",
    "treinar",
    "study",
    "review",
    "task",
)
SOCIAL_INTENT_KEYWORDS = (
    "bom dia",
    "boa tarde",
    "boa noite",
    "oi",
    "ola",
    "hello",
    "hi",
)
ENGLISH_ANXIETY_KEYWORDS = (
    "anxious",
    "anxiety",
    "nervous",
    "panic",
    "panicking",
    "scared",
    "afraid",
    "overwhelmed",
)
ENGLISH_EXAM_KEYWORDS = (
    "exam",
    "test",
    "presentation",
    "quiz",
    "assessment",
    "deadline",
)
ENGLISH_CATEGORY_HINTS = {
    "stress": (
        "anxious",
        "anxiety",
        "nervous",
        "stressed",
        "overwhelmed",
        "panic",
        "afraid",
        "scared",
    ),
    "duvida": (
        "doubt",
        "doubts",
        "confused",
        "confusing",
        "dont understand",
        "do not understand",
    ),
    "motivacao_baixa": (
        "unmotivated",
        "no motivation",
        "procrastinating",
        "cant start",
        "can't start",
    ),
    "cansaco_mental": (
        "tired",
        "exhausted",
        "drained",
        "burnout",
        "sleepy",
    ),
    "foco_alto": (
        "focused",
        "productive",
        "in the zone",
        "locked in",
    ),
    "evolucao": (
        "improved",
        "getting better",
        "made progress",
        "did it",
        "achieved",
        "finished",
        "i made it",
        "i did it",
        "conquered",
    ),
    "social": (
        "thanks",
        "thank you",
        "appreciate it",
        "grateful",
    ),
}
ENGLISH_CATEGORY_REPLIES = {
    "stress": [
        "I hear you. Let's reduce pressure now: what is the smallest step you can do first?",
        "Take a breath. What is pressing you the most today?",
        "If this feels like too much, let's choose just one priority for today.",
    ],
    "duvida": [
        "It is okay to have doubts. Which part feels most confusing?",
        "Tell me the topic and I can organize it into simple steps.",
        "What do you understand so far, even if it is just a little?",
    ],
    "motivacao_baixa": [
        "Let's just start: 15 minutes and done. Then you decide what comes next.",
        "Pick one small task. The goal is rhythm, not perfection.",
        "You don't need to do everything today. Just the first step.",
    ],
    "cansaco_mental": [
        "This sounds like mental fatigue. A short pause can help before continuing.",
        "Let's reduce the load: choose something light and quick now.",
        "If it feels heavy, we can split the task into two smaller parts.",
    ],
    "foco_alto": [
        "Great focus. Want to tackle the hardest task right now?",
        "Perfect. What is your number one priority to finish today?",
        "With focus this high, you can move one step ahead and gain margin later.",
    ],
    "evolucao": [
        "Great news. Want to share what helped you improve?",
        "That is real progress. Want to set your next small goal?",
        "Nice work. This consistency is paying off.",
    ],
    "social": [
        "Happy to help.",
        "Anytime you need, I'm here.",
        "You can count on me.",
    ],
}
ENGLISH_MICRO_INTERVENTIONS = {
    "beber agua": {
        "nome": "Drink water",
        "texto": "Pause for 1 minute and drink a glass of water to hydrate and regain clarity.",
    },
    "respiracao 4 4 4": {
        "nome": "Breathing 4-4-4",
        "texto": "Inhale for 4 seconds, hold for 4 seconds, and exhale for 4 seconds for 3 cycles.",
    },
}


def choose_variant(options: list[str], last_text: str | None) -> str:
    unique_options = list(dict.fromkeys(options or []))
    if not unique_options:
        return ""
    if last_text in unique_options and len(unique_options) > 1:
        filtered = [text for text in unique_options if text != last_text]
        return random.choice(filtered)
    return random.choice(unique_options)


def _normalize_text(value):
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    no_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    no_punctuation = re.sub(r"[^a-z0-9\s]", " ", no_accents)
    return re.sub(r"\s+", " ", no_punctuation).strip()


def _extract_keywords(raw_keywords):
    parts = re.split(r"[,\n;]+", str(raw_keywords or ""))
    cleaned = []
    for part in parts:
        keyword = _normalize_text(part.strip())
        if keyword:
            cleaned.append(keyword)
    return cleaned


def _contains_keyword(message_text, message_words, keyword):
    if not keyword:
        return False
    if " " in keyword:
        return keyword in message_text
    return keyword in message_words


def _has_any_keyword(message_text, keywords):
    if not message_text:
        return False
    message_words = set(message_text.split())
    for raw_keyword in keywords:
        keyword = _normalize_text(raw_keyword)
        if keyword and _contains_keyword(message_text, message_words, keyword):
            return True
    return False


def _matches_short_direction_intent(message_text):
    if not message_text:
        return False
    words = message_text.split()
    is_short = len(message_text) <= 20 or len(words) <= 3
    if not is_short:
        return False
    return _has_any_keyword(message_text, SHORT_DIRECTION_PATTERNS)


def _is_english_short_direction_message(message_text):
    return _has_any_keyword(message_text, SHORT_DIRECTION_ENGLISH_HINTS)


def _is_english_context(language_code, message_text):
    normalized_language = str(language_code or "").lower().replace("_", "-")
    if normalized_language.startswith("en"):
        return True
    return _has_any_keyword(
        message_text,
        (
            "what",
            "help me",
            "thanks",
            "thank you",
            "anxious",
            "nervous",
            "exam",
            "test",
        ),
    )


def _has_recent_stress_context(history):
    if not history:
        return False

    recent = history[:3]
    last_category = next(
        (item.categoria_detectada.slug for item in recent if item.categoria_detectada),
        None,
    )
    if last_category == "stress":
        return True

    last_user_message = _normalize_text(recent[0].mensagem_usuario) if recent[0].mensagem_usuario else ""
    return _has_any_keyword(last_user_message, SHORT_DIRECTION_CONTEXT_HINTS)


def _pick_short_direction_followup_reply(message_text, last_response_text):
    main_options_pt = CONTEXT_MESSAGES["stress_short_direction_main"]
    main_options_en = CONTEXT_MESSAGES["stress_short_direction_main_en"]
    is_pt_flow = last_response_text in main_options_pt
    is_en_flow = last_response_text in main_options_en

    if not is_pt_flow and not is_en_flow:
        return None

    if is_en_flow:
        if _has_any_keyword(message_text, SHORT_DIRECTION_POSITIVE_REPLIES_EN):
            return choose_variant(CONTEXT_MESSAGES["stress_short_direction_ok_en"], last_response_text)

        if _matches_short_direction_intent(message_text):
            return choose_variant(CONTEXT_MESSAGES["stress_short_direction_body_en"], last_response_text)

        if _has_any_keyword(message_text, SHORT_DIRECTION_NEGATIVE_REPLIES_EN):
            return choose_variant(CONTEXT_MESSAGES["stress_short_direction_body_en"], last_response_text)

        return None

    if _has_any_keyword(message_text, SHORT_DIRECTION_POSITIVE_REPLIES):
        return choose_variant(CONTEXT_MESSAGES["stress_short_direction_ok"], last_response_text)

    if _matches_short_direction_intent(message_text):
        return choose_variant(CONTEXT_MESSAGES["stress_short_direction_body"], last_response_text)

    if _has_any_keyword(message_text, SHORT_DIRECTION_NEGATIVE_REPLIES):
        return choose_variant(CONTEXT_MESSAGES["stress_short_direction_body"], last_response_text)

    return None


def _is_generic_question(message_text):
    if not message_text:
        return False
    words = message_text.split()
    is_short = len(message_text) <= 40 or len(words) <= 6
    if not is_short:
        return False
    return _has_any_keyword(message_text, GENERIC_QUESTION_PATTERNS)


def _was_blindagem_recently_activated(history):
    return any(item.resposta_texto == BLINDAGEM_REPLY for item in history[:3])


def _is_repeated_generic_question(message_text, history):
    if not history:
        return False
    if not _is_generic_question(message_text):
        return False
    last_message = _normalize_text(history[0].mensagem_usuario or "")
    return bool(last_message) and last_message == message_text


def _should_activate_blindagem(categoria, message_text, history):
    if categoria is not None or not history:
        return False

    last_categoria_null = history[0].categoria_detectada is None
    repeated_generic_question = _is_repeated_generic_question(message_text, history)
    return last_categoria_null or repeated_generic_question


def _resolve_categoria_by_slug(slug):
    if not slug:
        return None
    return CategoriaEmocional.objects.filter(slug=slug, ativo=True).first()


def _resolve_blindagem_choice(message_text, history):
    if not history:
        return None
    if history[0].resposta_texto != BLINDAGEM_REPLY:
        return None
    return BLINDAGEM_CATEGORY_MAP.get(message_text)


def _pick_greeting_reply(message_text):
    if not message_text:
        return None
    return GREETING_REPLIES.get(message_text)


def _compute_intent_scores(message_normalized):
    scores = {
        "emotional": 0,
        "task": 0,
        "event": 0,
        "social": 0,
        "general": 0,
    }
    if not message_normalized:
        scores["general"] = 1
        return scores

    has_emotional_keywords = _has_any_keyword(message_normalized, EMOTIONAL_INTENT_KEYWORDS)
    has_emotional_state = _has_any_keyword(message_normalized, ("to", "estou", "me sinto", "i feel"))
    has_exam_context = _has_any_keyword(message_normalized, ("prova", "apresentacao", "exam", "presentation"))
    if has_emotional_keywords:
        scores["emotional"] += 3
    if has_emotional_state:
        scores["emotional"] += 2
    if has_exam_context and (has_emotional_keywords or has_emotional_state):
        scores["emotional"] += 2

    has_date = _has_date_hint(message_normalized)
    has_time = _has_time_hint(message_normalized)

    if _has_any_keyword(message_normalized, TASK_INTENT_KEYWORDS):
        scores["task"] += 3
    if _has_any_keyword(message_normalized, ("preciso", "tenho que", "need to", "have to")):
        scores["task"] += 2
    if has_date and not has_time:
        scores["task"] += 1

    if _has_any_keyword(message_normalized, (*EVENT_CREATION_KEYWORDS, *EVENT_COMMITMENT_KEYWORDS)):
        scores["event"] += 3
    if has_time:
        scores["event"] += 3
    if has_date and has_time:
        scores["event"] += 2

    if _has_any_keyword(message_normalized, SOCIAL_INTENT_KEYWORDS):
        scores["social"] += 3
    if len(message_normalized.split()) <= 3:
        scores["social"] += 1

    if not any(value > 0 for key, value in scores.items() if key != "general"):
        scores["general"] = 1

    return scores


def _decide_mode(scores, has_pending, pending_action=None):
    emotional_score = int(scores.get("emotional", 0))
    if has_pending:
        if emotional_score >= 4:
            return "emotional_support"
        if pending_action == EVENT_CONCIERGE_ACTION:
            return "event"
        if pending_action == TASK_CONCIERGE_ACTION:
            return "task"
        return "general"

    if emotional_score >= 4:
        return "emotional_support"

    priority = ("event", "task", "social", "general")
    best_score = max(int(scores.get(mode, 0)) for mode in priority)
    if best_score <= 0:
        return "general"
    for mode in priority:
        if int(scores.get(mode, 0)) == best_score:
            return mode
    return "general"


def _parse_due_time_from_text(normalized_message):
    if not normalized_message:
        return None

    # Prioridade 1: formato com minutos explícitos (ex.: 09:00, 9h30).
    explicit_with_minutes = list(
        re.finditer(r"(?<!\d)([01]?\d|2[0-3])\s*(?::|h)\s*([0-5]\d)(?!\d)", normalized_message)
    )
    if explicit_with_minutes:
        match = explicit_with_minutes[-1]
        hour = int(match.group(1))
        minute = int(match.group(2))
        return timezone.datetime(2000, 1, 1, hour, minute).time()

    # Prioridade 2: formato de hora com marcador (ex.: 18h, 10 horas, as 14h).
    explicit_hour_only = list(
        re.finditer(r"(?<!\d)([01]?\d|2[0-3])\s*(?:h\b|hora\b|horas\b)", normalized_message)
    )
    if explicit_hour_only:
        match = explicit_hour_only[-1]
        hour = int(match.group(1))
        return timezone.datetime(2000, 1, 1, hour, 0).time()

    # Prioridade 3: hora por extenso (ex.: dez e meia, dez horas).
    textual_with_minutes = list(
        re.finditer(
            rf"(?<![a-z0-9])(?P<hour>{PORTUGUESE_HOUR_WORDS_PATTERN})\s+e\s+"
            rf"(?P<minute>{PORTUGUESE_MINUTE_WORDS_PATTERN})(?![a-z0-9])",
            normalized_message,
        )
    )
    if textual_with_minutes:
        match = textual_with_minutes[-1]
        hour = PORTUGUESE_HOUR_WORDS[match.group("hour")]
        minute = PORTUGUESE_MINUTE_WORDS[match.group("minute")]
        return timezone.datetime(2000, 1, 1, hour, minute).time()

    textual_hour_only = list(
        re.finditer(
            rf"(?<![a-z0-9])(?P<hour>{PORTUGUESE_HOUR_WORDS_PATTERN})\s*(?:hora\b|horas\b)(?![a-z0-9])",
            normalized_message,
        )
    )
    if textual_hour_only:
        match = textual_hour_only[-1]
        hour = PORTUGUESE_HOUR_WORDS[match.group("hour")]
        return timezone.datetime(2000, 1, 1, hour, 0).time()

    return None


def _normalize_datetime_text(value):
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    no_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    keep_chars = re.sub(r"[^a-z0-9\s/:-]", " ", no_accents)
    return re.sub(r"\s+", " ", keep_chars).strip()


def _parse_due_date_and_time_from_text(raw_message, normalized_message):
    today = timezone.localdate()
    raw_datetime_text = _normalize_datetime_text(raw_message)
    due_time = _parse_due_time_from_text(raw_datetime_text)

    if "amanha" in normalized_message:
        return today + timedelta(days=1), due_time
    if "hoje" in normalized_message:
        return today, due_time

    explicit_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", raw_datetime_text)
    if explicit_match:
        day = int(explicit_match.group(1))
        month = int(explicit_match.group(2))
        year_raw = explicit_match.group(3)
        if year_raw:
            year = int(year_raw)
            if year < 100:
                year += 2000
        else:
            year = today.year
        try:
            return date(year, month, day), due_time
        except ValueError:
            return None, due_time

    for weekday, weekday_index in WEEKDAY_MAP.items():
        if re.search(rf"\b{weekday}\b", normalized_message):
            days_ahead = (weekday_index - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead), due_time

    return None, due_time


def _strip_greeting_prefix(text):
    cleaned = text.strip()
    for prefix in TASK_GREETING_PREFIXES:
        if cleaned == prefix:
            return ""
        if cleaned.startswith(prefix + " "):
            return cleaned[len(prefix) :].strip()
    return cleaned


def _has_task_creation_intent(normalized_message):
    if _has_any_keyword(normalized_message, TASK_CREATION_KEYWORDS):
        return True

    if "tarefa" not in normalized_message:
        return False

    message_words = set(normalized_message.split())
    for action in TASK_CREATION_ACTION_HINTS:
        if _contains_keyword(normalized_message, message_words, action):
            return True
    return False


def _has_date_hint(normalized_message):
    if not normalized_message:
        return False
    if _has_any_keyword(normalized_message, ("hoje", "amanha", *WEEKDAY_MAP.keys())):
        return True
    return bool(re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", normalized_message))


def _has_time_hint(normalized_message):
    if not normalized_message:
        return False
    if _parse_due_time_from_text(normalized_message):
        return True
    return bool(re.search(r"\b([01]?\d|2[0-3])h(?:[0-5]\d)?\b", normalized_message))


def _has_event_creation_intent(normalized_message):
    if not normalized_message:
        return False

    has_event_keyword = _has_any_keyword(normalized_message, EVENT_CREATION_KEYWORDS)
    if has_event_keyword:
        return True

    has_commitment_hint = _has_any_keyword(normalized_message, EVENT_COMMITMENT_KEYWORDS)
    return has_commitment_hint and _has_date_hint(normalized_message) and _has_time_hint(normalized_message)


def _extract_task_title(normalized_message):
    cleaned = _strip_greeting_prefix(normalized_message)
    for prefix in TASK_TRIGGER_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
            break

    if ":" in cleaned:
        prefix_part, suffix_part = cleaned.split(":", 1)
        if "tarefa" in prefix_part and suffix_part.strip():
            cleaned = suffix_part.strip()

    if cleaned.startswith("pra mim "):
        cleaned = cleaned[8:].strip()
    if cleaned.startswith("para mim "):
        cleaned = cleaned[9:].strip()
    cleaned = re.sub(r"^executar\s+", "", cleaned).strip()
    cleaned = re.sub(r"^entre\s+hoje\s+e+\s+amanha\s*", "", cleaned).strip()
    cleaned = re.sub(r"\s+(hoje|amanha)\b.*$", "", cleaned).strip()
    cleaned = re.sub(r"\s+\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?(?:\s+\d{1,2}(?::\d{2})?\s*h?)?$", "", cleaned).strip()
    cleaned = re.sub(r"\s+(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:\s+\d{1,2}(?::\d{2})?\s*h?)?$", "", cleaned).strip()

    if not cleaned:
        return "Tarefa criada pelo chat"

    cleaned = re.sub(r"^(para|de|do|da|pra)\s+", "", cleaned).strip()
    cleaned = cleaned.strip(" \"'")
    if not cleaned:
        return "Tarefa criada pelo chat"
    return cleaned[:200]


def _extract_event_title(normalized_message):
    cleaned = _strip_greeting_prefix(normalized_message)
    for prefix in EVENT_TRIGGER_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
            break

    if cleaned.startswith("pra mim "):
        cleaned = cleaned[8:].strip()
    if cleaned.startswith("para mim "):
        cleaned = cleaned[9:].strip()

    cleaned = re.sub(r"^um\s+", "", cleaned).strip()
    cleaned = re.sub(r"^uma\s+", "", cleaned).strip()
    cleaned = re.sub(r"^novo\s+", "", cleaned).strip()
    cleaned = re.sub(r"^nova\s+", "", cleaned).strip()
    cleaned = re.sub(r"\b(hoje|amanha)\b.*$", "", cleaned).strip()
    cleaned = re.sub(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b.*$", "", cleaned).strip()
    cleaned = re.sub(r"\b([01]?\d|2[0-3])\s*(?::|h)\s*[0-5]?\d?\b.*$", "", cleaned).strip()
    cleaned = re.sub(r"\s+(segunda|terca|quarta|quinta|sexta|sabado|domingo)\b.*$", "", cleaned).strip()
    cleaned = cleaned.strip(" \"'")

    if not cleaned:
        return "Evento criado pelo chat"
    return cleaned[:200]


def _extract_clear_title_candidate(raw_message, normalized_message):
    quote_match = re.search(r'"([^"]{3,200})"', raw_message)
    if quote_match:
        return quote_match.group(1).strip()

    if ":" in raw_message:
        prefix, suffix = raw_message.split(":", 1)
        if "tarefa" in _normalize_text(prefix) and suffix.strip():
            return suffix.strip().strip(" \"'")[:200]

    fallback = _extract_task_title(normalized_message)
    fallback_normalized = _normalize_text(fallback)
    if re.fullmatch(r"(quero\s+)?(criar|crie|criasse)\s+(uma\s+)?(seguinte\s+)?tarefa", fallback_normalized):
        return ""
    if fallback and fallback != "Tarefa criada pelo chat" and len(fallback.split()) >= 2:
        return fallback
    return ""


def _extract_clear_event_title_candidate(raw_message, normalized_message):
    if _has_any_keyword(normalized_message, EVENT_GENERIC_REQUEST_PATTERNS) and not _has_any_keyword(
        normalized_message, EVENT_COMMITMENT_KEYWORDS
    ):
        return ""

    quote_match = re.search(r'"([^"]{3,200})"', raw_message)
    if quote_match:
        return quote_match.group(1).strip()

    if ":" in raw_message:
        prefix, suffix = raw_message.split(":", 1)
        prefix_normalized = _normalize_text(prefix)
        if suffix.strip() and (_has_any_keyword(prefix_normalized, EVENT_CREATION_KEYWORDS) or "agenda" in prefix_normalized):
            return suffix.strip().strip(" \"'")[:200]

    fallback = _extract_event_title(normalized_message)
    generic_event_titles = {
        "evento",
        "reuniao",
        "consulta",
        "aula",
        "compromisso",
        "agenda",
        "prova",
        "entrega",
        "seminario",
        "apresentacao",
    }
    if fallback and fallback != "Evento criado pelo chat":
        if fallback in generic_event_titles:
            return ""
        if len(fallback.split()) >= 2:
            return fallback
    return ""


def _resolve_event_type_choice(normalized_text):
    if _has_any_keyword(normalized_text, ("prova", "teste", "exame")):
        return EVENT_PROVA
    if _has_any_keyword(normalized_text, ("entrega", "prazo", "trabalho")):
        return EVENT_ENTREGA
    if _has_any_keyword(normalized_text, ("apresentacao", "seminario", "banca")):
        return EVENT_APRESENTACAO
    if _has_any_keyword(normalized_text, ("aula",)):
        return EVENT_AULA_IMPORTANTE
    if _has_any_keyword(normalized_text, ("reuniao com professor", "professor", "orientador")):
        return EVENT_REUNIAO_PROFESSORES
    if _has_any_keyword(normalized_text, ("reuniao", "grupo", "time")):
        return EVENT_REUNIAO_GRUPO
    if _has_any_keyword(normalized_text, ("estudar", "estudo", "revisar")):
        return EVENT_ESTUDAR_FACULDADE
    if _has_any_keyword(normalized_text, ("outro",)):
        return EVENT_OUTRO
    return None


def _strip_pending_event_type_marker(description):
    raw = str(description or "")
    return re.sub(r"^\[event_type:[A-Z_]+\]\s*", "", raw).strip()


def _extract_pending_event_type(pending):
    match = re.match(r"^\[event_type:([A-Z_]+)\]\s*", str(pending.draft_description or ""))
    if not match:
        return None
    return match.group(1)


def _set_pending_event_type(pending, event_type):
    cleaned_description = _strip_pending_event_type_marker(pending.draft_description)
    marker = f"[event_type:{event_type}]"
    pending.draft_description = f"{marker}\n{cleaned_description}".strip() if cleaned_description else marker


def _resolve_event_type(normalized_text):
    if _has_any_keyword(normalized_text, ("prova", "teste", "exame")):
        return EVENT_PROVA
    if _has_any_keyword(normalized_text, ("entrega", "prazo")):
        return EVENT_ENTREGA
    if _has_any_keyword(normalized_text, ("apresentacao", "seminario", "banca")):
        return EVENT_APRESENTACAO
    if _has_any_keyword(normalized_text, ("aula",)):
        return EVENT_AULA_IMPORTANTE
    if _has_any_keyword(normalized_text, ("professor", "orientador")):
        return EVENT_REUNIAO_PROFESSORES
    if _has_any_keyword(normalized_text, ("reuniao", "grupo", "time")):
        return EVENT_REUNIAO_GRUPO
    if _has_any_keyword(normalized_text, ("estudar", "estudo", "revisar")):
        return EVENT_ESTUDAR_FACULDADE
    return EVENT_OUTRO


def _format_event_when(start_at):
    local_value = timezone.localtime(start_at)
    return local_value.strftime("%d/%m/%Y %H:%M")


def _load_pending_action(user, now):
    pending = ChatPendingAction.objects.filter(user=user).first()
    if not pending:
        return None
    if pending.pending_action not in {TASK_CONCIERGE_ACTION, EVENT_CONCIERGE_ACTION}:
        pending.delete()
        return None
    expiration_limit = now - timedelta(minutes=TASK_CONCIERGE_EXPIRATION_MINUTES)
    if pending.updated_at < expiration_limit:
        pending.delete()
        return None
    return pending


def _is_cancel_pending_message(normalized_message):
    if not normalized_message:
        return False
    words = normalized_message.split()
    if normalized_message in {"cancelar", "parar", "deixa", "deixa pra la", "deixa para la"}:
        return True
    if normalized_message.startswith("cancelar "):
        return True
    if len(words) <= 2 and normalized_message in {"nao", "não"}:
        return True
    return False


def _is_emotional_urgent_message(categoria, normalized_message):
    if categoria and categoria.slug in {"stress", "motivacao_baixa", "cansaco_mental"}:
        return True
    if _has_any_keyword(normalized_message, ANXIETY_KEYWORDS):
        return True
    return _has_any_keyword(normalized_message, TASK_URGENT_KEYWORDS)


def _detect_categoria(message_text, is_english=False):
    if not message_text:
        return None

    message_words = set(message_text.split())
    has_negative_keywords = _has_any_keyword(message_text, NEGATIVE_KEYWORDS)
    gatilhos = GatilhoEmocional.objects.filter(ativo=True, categoria__ativo=True).select_related("categoria").order_by("id")
    score_by_slug = defaultdict(int)
    category_by_slug = {}

    for gatilho in gatilhos:
        categoria = gatilho.categoria
        slug = categoria.slug
        category_by_slug[slug] = categoria
        keywords = _extract_keywords(gatilho.palavras_chave)
        for keyword in keywords:
            if _contains_keyword(message_text, message_words, keyword):
                if keyword in WEAK_POSITIVE_KEYWORDS and has_negative_keywords:
                    weight = 0
                else:
                    weight = 2 if " " in keyword else 1
                score_by_slug[slug] += weight

    if is_english:
        for slug, hints in ENGLISH_CATEGORY_HINTS.items():
            categoria = category_by_slug.get(slug)
            if not categoria:
                categoria = (
                    GatilhoEmocional.objects.filter(categoria__slug=slug, categoria__ativo=True)
                    .select_related("categoria")
                    .first()
                )
                categoria = categoria.categoria if categoria else None
                if categoria:
                    category_by_slug[slug] = categoria
            if not categoria:
                continue
            for hint in hints:
                normalized_hint = _normalize_text(hint)
                if _contains_keyword(message_text, message_words, normalized_hint):
                    score_by_slug[slug] += 2 if " " in normalized_hint else 1

    if not score_by_slug:
        return None

    max_score = max(score_by_slug.values())
    if max_score <= 0:
        return None

    top_slugs = [slug for slug, score in score_by_slug.items() if score == max_score]

    # Optional UX rule: social should win ties only for clear/short gratitude signals.
    if "social" in top_slugs and len(top_slugs) > 1:
        is_short_message = len(message_text) <= 40
        has_social_hint = any(hint in message_text for hint in SOCIAL_STRONG_HINTS)
        if not (is_short_message or has_social_hint):
            filtered = [slug for slug in top_slugs if slug != "social"]
            if filtered:
                top_slugs = filtered

    for priority_slug in CATEGORY_PRIORITY:
        if priority_slug in top_slugs:
            return category_by_slug.get(priority_slug)

    chosen_slug = sorted(top_slugs)[0]
    return category_by_slug.get(chosen_slug)


def _pick_category_reply(categoria, last_response_text, is_english=False):
    if is_english:
        english_replies = ENGLISH_CATEGORY_REPLIES.get(categoria.slug) or []
        if english_replies:
            return choose_variant(english_replies, last_response_text)

    respostas = list(RespostaEmocional.objects.filter(categoria=categoria, ativo=True).values_list("texto", flat=True))
    if not respostas:
        return None
    return choose_variant(respostas, last_response_text)


def _load_recent_history(user):
    memory_hours = getattr(settings, "BRAIN_MEMORY_HOURS", 48)
    history_limit = getattr(settings, "BRAIN_HISTORY_LIMIT", 10)
    limite_48h = timezone.now() - timedelta(hours=memory_hours)
    return list(
        InteracaoAluno.objects.filter(user=user, created_at__gte=limite_48h)
        .select_related("categoria_detectada")
        .order_by("-created_at")[:history_limit]
    )


def _pick_contextual_reply(categoria, history, now, last_response_text, is_english=False):
    if not categoria:
        return None

    stress_threshold = getattr(settings, "BRAIN_STRESS_REPEAT_THRESHOLD", 3)
    evolucao_threshold = getattr(settings, "BRAIN_EVOLUCAO_REPEAT_THRESHOLD", 2)
    stress_to_evolucao_window = getattr(settings, "BRAIN_STRESS_TO_EVOLUCAO_WINDOW_HOURS", 24)

    current_slug = categoria.slug
    history_slugs = [item.categoria_detectada.slug for item in history if item.categoria_detectada]

    if current_slug == "stress":
        if len(history_slugs) >= stress_threshold and all(slug == "stress" for slug in history_slugs[:stress_threshold]):
            key = "stress_repeat_en" if is_english else "stress_repeat"
            return choose_variant(CONTEXT_MESSAGES[key], last_response_text)
        return None

    if current_slug == "evolucao":
        if len(history_slugs) >= evolucao_threshold and all(
            slug == "evolucao" for slug in history_slugs[:evolucao_threshold]
        ):
            key = "evolucao_repeat_en" if is_english else "evolucao_repeat"
            return choose_variant(CONTEXT_MESSAGES[key], last_response_text)

        limite_24h = now - timedelta(hours=stress_to_evolucao_window)
        has_recent_stress = any(
            item.categoria_detectada
            and item.categoria_detectada.slug == "stress"
            and item.created_at >= limite_24h
            for item in history
        )
        if has_recent_stress:
            key = "stress_to_evolucao_en" if is_english else "stress_to_evolucao"
            return choose_variant(CONTEXT_MESSAGES[key], last_response_text)

    return None


def _pick_micro_intervention(request, categoria, is_english=False):
    if not categoria or categoria.slug in {"social", "evolucao"}:
        return []

    options = list(MicroIntervencao.objects.filter(ativo=True).order_by("id"))
    if not options:
        return []

    session_key = "brain_last_micro_intervention_name"
    last_micro_name = request.session.get(session_key)

    candidates = options
    if last_micro_name and len(options) > 1:
        filtered = [item for item in options if item.nome != last_micro_name]
        if filtered:
            candidates = filtered

    selected = random.choice(candidates)
    request.session[session_key] = selected.nome

    if is_english:
        normalized_name = _normalize_text(selected.nome)
        translated = ENGLISH_MICRO_INTERVENTIONS.get(normalized_name)
        if translated:
            return [{"nome": translated["nome"], "texto": translated["texto"]}]

    return [{"nome": selected.nome, "texto": selected.texto}]


def _build_reply_for_categoria(categoria, normalized_message, history, now, last_response_text, is_english=False):
    if not categoria:
        fallback_options = ENGLISH_FALLBACK_REPLIES if is_english else FALLBACK_REPLIES
        return random.choice(fallback_options)

    reply_text = None
    if categoria.slug == "stress":
        anxiety_keywords = ENGLISH_ANXIETY_KEYWORDS if is_english else ANXIETY_KEYWORDS
        exam_keywords = ENGLISH_EXAM_KEYWORDS if is_english else EXAM_KEYWORDS
        has_anxiety = _has_any_keyword(normalized_message, anxiety_keywords)
        has_exam = _has_any_keyword(normalized_message, exam_keywords)
        if has_anxiety and has_exam:
            key = "stress_anxiety_en" if is_english else "stress_anxiety"
            reply_text = choose_variant(CONTEXT_MESSAGES[key], last_response_text)
        elif has_anxiety:
            key = "stress_anxiety_en" if is_english else "stress_anxiety"
            reply_text = choose_variant(CONTEXT_MESSAGES[key], last_response_text)

    if not reply_text:
        reply_text = _pick_contextual_reply(categoria, history, now, last_response_text, is_english=is_english)
    if not reply_text:
        reply_text = _pick_category_reply(categoria, last_response_text, is_english=is_english)
    if not reply_text:
        fallback_options = ENGLISH_FALLBACK_REPLIES if is_english else FALLBACK_REPLIES
        reply_text = random.choice(fallback_options)
    return reply_text


def _start_task_concierge(user, raw_message, normalized_message):
    title_candidate = _extract_clear_title_candidate(raw_message, normalized_message)
    step = 2 if title_candidate else 1
    pending, _ = ChatPendingAction.objects.get_or_create(
        user=user,
        defaults={"pending_action": TASK_CONCIERGE_ACTION},
    )
    pending.pending_action = TASK_CONCIERGE_ACTION
    pending.step = step
    pending.draft_title = title_candidate[:200] if title_candidate else ""
    pending.draft_description = (title_candidate or "").strip()[:2000]
    pending.draft_due_date = None
    pending.draft_due_time = None
    pending.save()
    return pending, (TASK_CONCIERGE_ASK_DUE if step == 2 else TASK_CONCIERGE_ASK_SCOPE)


def _start_event_concierge(user, raw_message, normalized_message):
    title_candidate = _extract_clear_event_title_candidate(raw_message, normalized_message)
    step = 2 if title_candidate else 1
    pending, _ = ChatPendingAction.objects.get_or_create(
        user=user,
        defaults={"pending_action": EVENT_CONCIERGE_ACTION},
    )
    pending.pending_action = EVENT_CONCIERGE_ACTION
    pending.step = step
    pending.draft_title = title_candidate[:200] if title_candidate else ""
    pending.draft_description = (title_candidate or "").strip()[:2000]
    pending.draft_due_date = None
    pending.draft_due_time = None
    pending.save()
    return pending, (EVENT_CONCIERGE_ASK_WHEN if step == 2 else EVENT_CONCIERGE_ASK_SCOPE)


def _finalize_task_from_pending(user, pending, raw_message, normalized_message):
    due_date, due_time = _parse_due_date_and_time_from_text(raw_message, normalized_message)
    if not due_date:
        pending.save()  # refresh updated_at for ongoing conversation
        return None, TASK_CONCIERGE_RETRY_DUE

    title = (pending.draft_title or "").strip() or "Tarefa criada pelo chat"
    duplicate_limit = timezone.now() - timedelta(minutes=2)
    duplicate_task_exists = Task.objects.filter(
        user=user,
        title__iexact=title,
        created_at__gte=duplicate_limit,
    ).exists()
    duplicate_notification_exists = InAppNotification.objects.filter(
        user=user,
        title="Tarefa criada",
        body=title,
        created_at__gte=duplicate_limit,
    ).exists()
    if duplicate_task_exists or duplicate_notification_exists:
        pending.delete()
        return None, "Essa tarefa ja foi criada agora ha pouco. Confira sua lista em Tarefas. 🔔"

    description = (pending.draft_description or "").strip()
    if due_time:
        suffix = f"Horario sugerido: {due_time.strftime('%H:%M')}"
        description = f"{description}\n\n{suffix}" if description else suffix

    task = Task.objects.create(
        user=user,
        title=title,
        description=description[:2000],
        due_date=due_date,
        stress_level=3,
        status=TASK_TODO,
    )
    target_url = f"{reverse('ui-task-list')}?highlight_task={task.id}"
    InAppNotification.objects.create(
        user=user,
        title="Tarefa criada",
        body=task.title,
        target_url=target_url,
        is_read=False,
    )
    pending.delete()
    return task, TASK_CONCIERGE_CONFIRM.format(title=task.title, due_date=due_date.strftime("%d/%m/%Y"))


def _finalize_event_from_pending(user, pending, raw_message, normalized_message):
    start_date, start_time = _parse_due_date_and_time_from_text(raw_message, normalized_message)
    explicit_event_type = _resolve_event_type_choice(normalized_message)

    if explicit_event_type and (not start_date or not start_time):
        _set_pending_event_type(pending, explicit_event_type)
        pending.step = 2
        pending.save(update_fields=["draft_description", "step", "updated_at"])
        return None, EVENT_CONCIERGE_ASK_ONLY_WHEN

    if not start_date or not start_time:
        pending.save()  # refresh updated_at for ongoing conversation
        return None, EVENT_CONCIERGE_RETRY_WHEN

    title = (pending.draft_title or "").strip() or "Evento criado pelo chat"
    duplicate_limit = timezone.now() - timedelta(minutes=2)
    start_naive = datetime.combine(start_date, start_time)
    start_at = timezone.make_aware(start_naive, timezone.get_current_timezone())
    duplicate_event_exists = CalendarEvent.objects.filter(
        user=user,
        title__iexact=title,
        start_at=start_at,
        created_at__gte=duplicate_limit,
    ).exists()
    duplicate_notification_exists = InAppNotification.objects.filter(
        user=user,
        title="Evento agendado",
        body=title,
        created_at__gte=duplicate_limit,
    ).exists()
    if duplicate_event_exists or duplicate_notification_exists:
        pending.delete()
        return None, "Esse evento ja foi criado agora ha pouco. Confira sua agenda. 🔔"

    pending_event_type = _extract_pending_event_type(pending)
    description = _strip_pending_event_type_marker(pending.draft_description)
    event_type = explicit_event_type or pending_event_type or _resolve_event_type(_normalize_text(f"{title} {description}"))
    end_at = start_at + timedelta(hours=1)
    event = CalendarEvent.objects.create(
        user=user,
        title=title,
        event_type=event_type,
        start_at=start_at,
        end_at=end_at,
        notes=description[:2000],
    )
    target_url = f"{reverse('ui-agenda-list')}?highlight_event={event.id}"
    InAppNotification.objects.create(
        user=user,
        title="Evento agendado",
        body=event.title,
        target_url=target_url,
        is_read=False,
    )
    pending.delete()
    return event, EVENT_CONCIERGE_CONFIRM.format(title=event.title, when=_format_event_when(start_at))


class WidgetChatView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WidgetChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mensagem_usuario = serializer.validated_data["message"].strip()
        normalized_message = _normalize_text(mensagem_usuario)
        is_english = _is_english_context(getattr(request, "LANGUAGE_CODE", ""), normalized_message)
        now = timezone.now()
        last_response_text = (
            InteracaoAluno.objects.filter(user=request.user)
            .order_by("-created_at", "-id")
            .values_list("resposta_texto", flat=True)
            .first()
        )
        historico = _load_recent_history(request.user)
        pending = _load_pending_action(request.user, now)
        intent_scores = _compute_intent_scores(normalized_message)
        mode = _decide_mode(
            intent_scores,
            has_pending=bool(pending),
            pending_action=pending.pending_action if pending else None,
        )

        # Bloco: Cancelamento de fluxo pendente
        if pending and _is_cancel_pending_message(normalized_message):
            pending.delete()
            InteracaoAluno.objects.create(
                user=request.user,
                mensagem_usuario=mensagem_usuario,
                categoria_detectada=None,
                resposta_texto=TASK_CONCIERGE_CANCEL,
                origem="widget",
            )
            return Response(
                {
                    "reply": TASK_CONCIERGE_CANCEL,
                    "category": None,
                    "emoji": None,
                    "micro_interventions": [],
                },
                status=status.HTTP_200_OK,
            )

        # Bloco: Fluxo concierge pendente em 2 etapas
        if pending:
            if mode == "emotional_support":
                categoria_pending = _detect_categoria(normalized_message, is_english=is_english)
                emotional_reply = _build_reply_for_categoria(
                    categoria_pending,
                    normalized_message,
                    historico,
                    now,
                    last_response_text,
                    is_english=is_english,
                )
                payload_micro = _pick_micro_intervention(request, categoria_pending, is_english=is_english)
                InteracaoAluno.objects.create(
                    user=request.user,
                    mensagem_usuario=mensagem_usuario,
                    categoria_detectada=categoria_pending,
                    resposta_texto=emotional_reply,
                    origem="widget",
                )
                return Response(
                    {
                        "reply": emotional_reply,
                        "category": categoria_pending.slug if categoria_pending else None,
                        "emoji": categoria_pending.emoji if categoria_pending else None,
                        "micro_interventions": payload_micro,
                    },
                    status=status.HTTP_200_OK,
                )

            if mode == "task" and pending.pending_action == TASK_CONCIERGE_ACTION:
                if pending.step == 1:
                    title_candidate = _extract_clear_title_candidate(mensagem_usuario, normalized_message) or _extract_task_title(
                        normalized_message
                    )
                    pending.draft_title = title_candidate[:200]
                    pending.draft_description = title_candidate[:2000]
                    pending.step = 2
                    pending.save()
                    reply_text = TASK_CONCIERGE_ASK_DUE
                else:
                    _task, reply_text = _finalize_task_from_pending(request.user, pending, mensagem_usuario, normalized_message)
            elif mode == "event" and pending.pending_action == EVENT_CONCIERGE_ACTION:
                if pending.step == 1:
                    title_candidate = _extract_clear_event_title_candidate(mensagem_usuario, normalized_message) or _extract_event_title(
                        normalized_message
                    )
                    pending.draft_title = title_candidate[:200]
                    pending.draft_description = title_candidate[:2000]
                    pending.step = 2
                    pending.save()
                    reply_text = EVENT_CONCIERGE_ASK_WHEN
                else:
                    _event, reply_text = _finalize_event_from_pending(request.user, pending, mensagem_usuario, normalized_message)
            else:
                pending.delete()
                fallback_options = ENGLISH_FALLBACK_REPLIES if is_english else FALLBACK_REPLIES
                reply_text = random.choice(fallback_options)

            categoria_fluxo = _resolve_categoria_by_slug("foco_alto")
            InteracaoAluno.objects.create(
                user=request.user,
                mensagem_usuario=mensagem_usuario,
                categoria_detectada=categoria_fluxo,
                resposta_texto=reply_text,
                origem="widget",
            )
            return Response(
                {
                    "reply": reply_text,
                    "category": categoria_fluxo.slug if categoria_fluxo else None,
                    "emoji": categoria_fluxo.emoji if categoria_fluxo else None,
                    "micro_interventions": [],
                },
                status=status.HTTP_200_OK,
            )

        event_start_signal = _has_event_creation_intent(normalized_message) or (
            _has_date_hint(normalized_message) and _has_time_hint(normalized_message)
        )

        # Bloco: Inicia fluxo concierge quando modo decidir evento.
        if mode == "event" and event_start_signal:
            _pending, reply_text = _start_event_concierge(request.user, mensagem_usuario, normalized_message)
            categoria_fluxo = _resolve_categoria_by_slug("foco_alto")
            InteracaoAluno.objects.create(
                user=request.user,
                mensagem_usuario=mensagem_usuario,
                categoria_detectada=categoria_fluxo,
                resposta_texto=reply_text,
                origem="widget",
            )
            return Response(
                {
                    "reply": reply_text,
                    "category": categoria_fluxo.slug if categoria_fluxo else None,
                    "emoji": categoria_fluxo.emoji if categoria_fluxo else None,
                    "micro_interventions": [],
                },
                status=status.HTTP_200_OK,
            )

        # Bloco: Inicia fluxo concierge quando modo decidir tarefa.
        if mode == "task" and _has_task_creation_intent(normalized_message):
            _pending, reply_text = _start_task_concierge(request.user, mensagem_usuario, normalized_message)
            categoria_fluxo = _resolve_categoria_by_slug("foco_alto")
            InteracaoAluno.objects.create(
                user=request.user,
                mensagem_usuario=mensagem_usuario,
                categoria_detectada=categoria_fluxo,
                resposta_texto=reply_text,
                origem="widget",
            )
            return Response(
                {
                    "reply": reply_text,
                    "category": categoria_fluxo.slug if categoria_fluxo else None,
                    "emoji": categoria_fluxo.emoji if categoria_fluxo else None,
                    "micro_interventions": [],
                },
                status=status.HTTP_200_OK,
            )

        # Bloco: social so retorna saudacao quando houver saudacao explicita.
        if mode == "social":
            greeting_reply = _pick_greeting_reply(normalized_message)
            if greeting_reply:
                InteracaoAluno.objects.create(
                    user=request.user,
                    mensagem_usuario=mensagem_usuario,
                    categoria_detectada=None,
                    resposta_texto=greeting_reply,
                    origem="widget",
                )
                return Response(
                    {
                        "reply": greeting_reply,
                        "category": None,
                        "emoji": None,
                        "micro_interventions": [],
                    },
                    status=status.HTTP_200_OK,
                )

        followup_reply = _pick_short_direction_followup_reply(normalized_message, last_response_text)
        if followup_reply:
            categoria_stress = _resolve_categoria_by_slug("stress")
            InteracaoAluno.objects.create(
                user=request.user,
                mensagem_usuario=mensagem_usuario,
                categoria_detectada=categoria_stress,
                resposta_texto=followup_reply,
                origem="widget",
            )
            return Response(
                {
                    "reply": followup_reply,
                    "category": categoria_stress.slug if categoria_stress else None,
                    "emoji": categoria_stress.emoji if categoria_stress else None,
                    "micro_interventions": [],
                },
                status=status.HTTP_200_OK,
            )

        blindagem_choice_slug = _resolve_blindagem_choice(normalized_message, historico)
        if blindagem_choice_slug:
            categoria = _resolve_categoria_by_slug(blindagem_choice_slug)
            if categoria:
                reply_text = _pick_category_reply(categoria, last_response_text, is_english=is_english)
            else:
                reply_text = None
            if not reply_text:
                fallback_options = ENGLISH_FALLBACK_REPLIES if is_english else FALLBACK_REPLIES
                reply_text = random.choice(fallback_options)
            payload_micro_intervencoes = _pick_micro_intervention(request, categoria, is_english=is_english)

            InteracaoAluno.objects.create(
                user=request.user,
                mensagem_usuario=mensagem_usuario,
                categoria_detectada=categoria,
                resposta_texto=reply_text,
                origem="widget",
            )
            return Response(
                {
                    "reply": reply_text,
                    "category": categoria.slug if categoria else None,
                    "emoji": categoria.emoji if categoria else None,
                    "micro_interventions": payload_micro_intervencoes,
                },
                status=status.HTTP_200_OK,
            )

        categoria = _detect_categoria(normalized_message, is_english=is_english)
        if _matches_short_direction_intent(normalized_message) and _has_recent_stress_context(historico):
            categoria = _resolve_categoria_by_slug("stress") or categoria
            if is_english and _is_english_short_direction_message(normalized_message):
                reply_text = choose_variant(CONTEXT_MESSAGES["stress_short_direction_main_en"], last_response_text)
            else:
                reply_text = choose_variant(CONTEXT_MESSAGES["stress_short_direction_main"], last_response_text)
            payload_micro_intervencoes = []
        elif categoria:
            reply_text = _build_reply_for_categoria(
                categoria,
                normalized_message,
                historico,
                now,
                last_response_text,
                is_english=is_english,
            )
            payload_micro_intervencoes = _pick_micro_intervention(request, categoria, is_english=is_english)
        else:
            should_activate_blindagem = _should_activate_blindagem(categoria, normalized_message, historico)
            if should_activate_blindagem:
                if _was_blindagem_recently_activated(historico):
                    reply_text = BLINDAGEM_NEUTRAL_REPLY
                else:
                    reply_text = BLINDAGEM_REPLY
            else:
                fallback_options = ENGLISH_FALLBACK_REPLIES if is_english else FALLBACK_REPLIES
                reply_text = random.choice(fallback_options)
            payload_micro_intervencoes = []

        InteracaoAluno.objects.create(
            user=request.user,
            mensagem_usuario=mensagem_usuario,
            categoria_detectada=categoria,
            resposta_texto=reply_text,
            origem="widget",
        )

        return Response(
            {
                "reply": reply_text,
                "category": categoria.slug if categoria else None,
                "emoji": categoria.emoji if categoria else None,
                "micro_interventions": payload_micro_intervencoes,
            },
            status=status.HTTP_200_OK,
        )
