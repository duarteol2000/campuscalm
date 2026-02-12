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

from brain.constants import CONTEXT_MESSAGES
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


def _detect_categoria(message_text):
    if not message_text:
        return None

    message_words = set(message_text.split())
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


def _pick_category_reply(categoria, user):
    respostas = list(RespostaEmocional.objects.filter(categoria=categoria, ativo=True).values_list("texto", flat=True))
    if not respostas:
        return None

    chosen = random.choice(respostas)
    last_interaction = InteracaoAluno.objects.filter(user=user).order_by("-created_at", "-id").first()
    unique_responses = set(respostas)
    if len(unique_responses) > 1 and last_interaction and chosen == last_interaction.resposta_texto:
        alternatives = [text for text in unique_responses if text != last_interaction.resposta_texto]
        if alternatives:
            chosen = random.choice(alternatives)
    return chosen


def _load_recent_history(user):
    memory_hours = getattr(settings, "BRAIN_MEMORY_HOURS", 48)
    history_limit = getattr(settings, "BRAIN_HISTORY_LIMIT", 10)
    limite_48h = timezone.now() - timedelta(hours=memory_hours)
    return list(
        InteracaoAluno.objects.filter(user=user, created_at__gte=limite_48h)
        .select_related("categoria_detectada")
        .order_by("-created_at")[:history_limit]
    )


def _pick_contextual_reply(categoria, history, now):
    if not categoria:
        return None

    stress_threshold = getattr(settings, "BRAIN_STRESS_REPEAT_THRESHOLD", 3)
    evolucao_threshold = getattr(settings, "BRAIN_EVOLUCAO_REPEAT_THRESHOLD", 2)
    stress_to_evolucao_window = getattr(settings, "BRAIN_STRESS_TO_EVOLUCAO_WINDOW_HOURS", 24)

    current_slug = categoria.slug
    history_slugs = [item.categoria_detectada.slug for item in history if item.categoria_detectada]

    if current_slug == "stress":
        if len(history_slugs) >= stress_threshold and all(slug == "stress" for slug in history_slugs[:stress_threshold]):
            return CONTEXT_MESSAGES["stress_repeat"]
        return None

    if current_slug == "evolucao":
        if len(history_slugs) >= evolucao_threshold and all(
            slug == "evolucao" for slug in history_slugs[:evolucao_threshold]
        ):
            return CONTEXT_MESSAGES["evolucao_repeat"]

        limite_24h = now - timedelta(hours=stress_to_evolucao_window)
        has_recent_stress = any(
            item.categoria_detectada
            and item.categoria_detectada.slug == "stress"
            and item.created_at >= limite_24h
            for item in history
        )
        if has_recent_stress:
            return CONTEXT_MESSAGES["stress_to_evolucao"]

    return None


class WidgetChatView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WidgetChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mensagem_usuario = serializer.validated_data["message"].strip()
        normalized_message = _normalize_text(mensagem_usuario)
        now = timezone.now()

        categoria = _detect_categoria(normalized_message)
        if categoria:
            historico = _load_recent_history(request.user)
            reply_text = _pick_contextual_reply(categoria, historico, now)
            if not reply_text:
                reply_text = _pick_category_reply(categoria, request.user)
            if not reply_text:
                reply_text = random.choice(FALLBACK_REPLIES)
            if categoria.slug in {"social", "evolucao"}:
                payload_micro_intervencoes = []
            else:
                micro_intervencoes = MicroIntervencao.objects.filter(ativo=True).order_by("id")[:2]
                payload_micro_intervencoes = [{"nome": item.nome, "texto": item.texto} for item in micro_intervencoes]
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
