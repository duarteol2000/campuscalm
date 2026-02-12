import re
import random
import unicodedata

from rest_framework import permissions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from brain.models import GatilhoEmocional, InteracaoAluno, MicroIntervencao, RespostaEmocional


class WidgetChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)


FALLBACK_REPLIES = [
    "Estou aqui com voce. Quer me contar um pouco mais sobre isso?",
    "Entendi. Me fala um pouco mais para eu poder te ajudar melhor.",
]


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
    message_words = set(message_text.split())
    gatilhos = GatilhoEmocional.objects.filter(ativo=True, categoria__ativo=True).select_related("categoria").order_by("id")
    for gatilho in gatilhos:
        keywords = _extract_keywords(gatilho.palavras_chave)
        if any(_contains_keyword(message_text, message_words, keyword) for keyword in keywords):
            return gatilho.categoria
    return None


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


class WidgetChatView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WidgetChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mensagem_usuario = serializer.validated_data["message"].strip()
        normalized_message = _normalize_text(mensagem_usuario)

        categoria = _detect_categoria(normalized_message)
        if categoria:
            reply_text = _pick_category_reply(categoria, request.user)
            if not reply_text:
                reply_text = random.choice(FALLBACK_REPLIES)
            if categoria.slug == "social":
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
