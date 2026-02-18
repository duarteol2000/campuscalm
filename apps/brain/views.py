import re
import random
import unicodedata
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework import permissions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from brain.constants import ANXIETY_KEYWORDS, CONTEXT_MESSAGES, EXAM_KEYWORDS
from brain.models import CategoriaEmocional, GatilhoEmocional, InteracaoAluno, MicroIntervencao, RespostaEmocional


class WidgetChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)


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
                reply_text = _pick_contextual_reply(categoria, historico, now, last_response_text, is_english=is_english)
            if not reply_text:
                reply_text = _pick_category_reply(categoria, last_response_text, is_english=is_english)
            if not reply_text:
                fallback_options = ENGLISH_FALLBACK_REPLIES if is_english else FALLBACK_REPLIES
                reply_text = random.choice(fallback_options)
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
