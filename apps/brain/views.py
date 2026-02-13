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
from brain.models import GatilhoEmocional, InteracaoAluno, MicroIntervencao, RespostaEmocional


class WidgetChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)


FALLBACK_REPLIES = [
    "Estou aqui com voce. Quer me contar um pouco mais sobre isso?",
    "Entendi. Me fala um pouco mais para eu poder te ajudar melhor.",
]

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
    "e agora",
    "me ajuda",
    "socorro",
    "nao sei",
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
    return any(pattern in message_text for pattern in SHORT_DIRECTION_PATTERNS)


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
    return any(hint in last_user_message for hint in SHORT_DIRECTION_CONTEXT_HINTS)


def _pick_short_direction_followup_reply(message_text, last_response_text):
    main_options = CONTEXT_MESSAGES["stress_short_direction_main"]
    if last_response_text not in main_options:
        return None

    if any(term in message_text for term in SHORT_DIRECTION_POSITIVE_REPLIES):
        return choose_variant(CONTEXT_MESSAGES["stress_short_direction_ok"], last_response_text)

    if _matches_short_direction_intent(message_text):
        return choose_variant(CONTEXT_MESSAGES["stress_short_direction_body"], last_response_text)

    if any(term in message_text for term in SHORT_DIRECTION_NEGATIVE_REPLIES):
        return choose_variant(CONTEXT_MESSAGES["stress_short_direction_body"], last_response_text)

    return None


def _detect_categoria(message_text):
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


def _pick_category_reply(categoria, last_response_text):
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


def _pick_contextual_reply(categoria, history, now, last_response_text):
    if not categoria:
        return None

    stress_threshold = getattr(settings, "BRAIN_STRESS_REPEAT_THRESHOLD", 3)
    evolucao_threshold = getattr(settings, "BRAIN_EVOLUCAO_REPEAT_THRESHOLD", 2)
    stress_to_evolucao_window = getattr(settings, "BRAIN_STRESS_TO_EVOLUCAO_WINDOW_HOURS", 24)

    current_slug = categoria.slug
    history_slugs = [item.categoria_detectada.slug for item in history if item.categoria_detectada]

    if current_slug == "stress":
        if len(history_slugs) >= stress_threshold and all(slug == "stress" for slug in history_slugs[:stress_threshold]):
            return choose_variant(CONTEXT_MESSAGES["stress_repeat"], last_response_text)
        return None

    if current_slug == "evolucao":
        if len(history_slugs) >= evolucao_threshold and all(
            slug == "evolucao" for slug in history_slugs[:evolucao_threshold]
        ):
            return choose_variant(CONTEXT_MESSAGES["evolucao_repeat"], last_response_text)

        limite_24h = now - timedelta(hours=stress_to_evolucao_window)
        has_recent_stress = any(
            item.categoria_detectada
            and item.categoria_detectada.slug == "stress"
            and item.created_at >= limite_24h
            for item in history
        )
        if has_recent_stress:
            return choose_variant(CONTEXT_MESSAGES["stress_to_evolucao"], last_response_text)

    return None


def _pick_micro_intervention(request, categoria):
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
    return [{"nome": selected.nome, "texto": selected.texto}]


class WidgetChatView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WidgetChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mensagem_usuario = serializer.validated_data["message"].strip()
        normalized_message = _normalize_text(mensagem_usuario)
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
            categoria = GatilhoEmocional.objects.filter(categoria__slug="stress", categoria__ativo=True).select_related(
                "categoria"
            ).first()
            categoria_stress = categoria.categoria if categoria else None
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

        categoria = _detect_categoria(normalized_message)
        if _matches_short_direction_intent(normalized_message) and _has_recent_stress_context(historico):
            categoria_match = GatilhoEmocional.objects.filter(
                categoria__slug="stress",
                categoria__ativo=True,
            ).select_related("categoria").first()
            categoria = categoria_match.categoria if categoria_match else categoria
            reply_text = choose_variant(CONTEXT_MESSAGES["stress_short_direction_main"], last_response_text)
            payload_micro_intervencoes = []
        elif categoria:
            reply_text = None
            if categoria.slug == "stress":
                has_anxiety = _has_any_keyword(normalized_message, ANXIETY_KEYWORDS)
                has_exam = _has_any_keyword(normalized_message, EXAM_KEYWORDS)
                if has_anxiety and has_exam:
                    reply_text = choose_variant(CONTEXT_MESSAGES["stress_anxiety"], last_response_text)
                elif has_anxiety:
                    reply_text = choose_variant(CONTEXT_MESSAGES["stress_anxiety"], last_response_text)

            if not reply_text:
                reply_text = _pick_contextual_reply(categoria, historico, now, last_response_text)
            if not reply_text:
                reply_text = _pick_category_reply(categoria, last_response_text)
            if not reply_text:
                reply_text = random.choice(FALLBACK_REPLIES)
            payload_micro_intervencoes = _pick_micro_intervention(request, categoria)
        else:
            reply_text = random.choice(FALLBACK_REPLIES)
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
