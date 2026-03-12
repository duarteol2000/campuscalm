from __future__ import annotations

import re
import unicodedata
from datetime import timedelta

from django.utils import timezone

from learning.models import StudySession
from learning.services.discipline_score import calculate_score_payload, latest_score
from utils.localization import get_user_language, localized_text


SUBJECT_ALIASES = {
    "matematica": {
        "matematica",
        "matematicaa",
        "mat",
        "matemat",
    },
    "portugues": {
        "portugues",
        "portguês",
        "portgues",
        "port",
        "portuguess",
    },
    "fisica": {
        "fisica",
        "fisic",
        "fisca",
    },
    "quimica": {
        "quimica",
        "quimca",
        "quimic",
    },
    "biologia": {
        "biologia",
        "biologa",
        "bio",
    },
}

SUBJECT_LABELS = {
    "matematica": {"pt-BR": "Matemática", "en": "Math", "es": "Matemáticas"},
    "portugues": {"pt-BR": "Português", "en": "Portuguese", "es": "Portugués"},
    "fisica": {"pt-BR": "Física", "en": "Physics", "es": "Física"},
    "quimica": {"pt-BR": "Química", "en": "Chemistry", "es": "Química"},
    "biologia": {"pt-BR": "Biologia", "en": "Biology", "es": "Biología"},
}

SUBJECT_GUIDANCE = {
    "matematica": {
        "pt-BR": [
            "Pratique exercícios todos os dias, começando pelos mais simples.",
            "Revise cada erro com calma e depois refaça sem consultar.",
            "Resolva problemas passo a passo e treine interpretação de enunciados.",
            "Leia bons livros para fortalecer raciocínio e compreensão textual.",
        ],
        "en": [
            "Practice exercises every day, starting with simpler ones.",
            "Review each mistake carefully and then solve it again without checking.",
            "Work through problems step by step and train statement interpretation.",
            "Read good books to strengthen reasoning and text comprehension.",
        ],
        "es": [
            "Practica ejercicios todos los días, empezando por los más simples.",
            "Revisa cada error con calma y luego reházlo sin consultar.",
            "Resuelve problemas paso a paso y entrena la interpretación de enunciados.",
            "Lee buenos libros para fortalecer el razonamiento y la comprensión textual.",
        ],
    },
    "portugues": {
        "pt-BR": [
            "Mantenha leitura diária para ampliar vocabulário e interpretação.",
            "Faça resumos curtos e revisão gramatical frequente.",
            "Treine escrita prática com atenção à clareza e estrutura.",
            "Leia bons livros para melhorar repertório e compreensão.",
        ],
        "en": [
            "Keep a daily reading habit to expand vocabulary and interpretation.",
            "Write short summaries and review grammar often.",
            "Practice writing with attention to clarity and structure.",
            "Read good books to improve repertoire and comprehension.",
        ],
        "es": [
            "Mantén lectura diaria para ampliar vocabulario e interpretación.",
            "Haz resúmenes cortos y revisión gramatical frecuente.",
            "Practica escritura con atención a la claridad y la estructura.",
            "Lee buenos libros para mejorar repertorio y comprensión.",
        ],
    },
    "fisica": {
        "pt-BR": [
            "Entenda os conceitos antes de decorar fórmulas.",
            "Resolva exercícios passo a passo e conecte com exemplos do cotidiano.",
            "Revise conteúdos anteriores para não perder a base.",
            "Leia com atenção os enunciados para melhorar raciocínio e interpretação.",
        ],
        "en": [
            "Understand the concepts before memorizing formulas.",
            "Solve exercises step by step and connect them to real-life examples.",
            "Review previous topics so the foundation stays solid.",
            "Read statements carefully to improve reasoning and interpretation.",
        ],
        "es": [
            "Entiende los conceptos antes de memorizar fórmulas.",
            "Resuelve ejercicios paso a paso y relaciónalos con ejemplos cotidianos.",
            "Revisa contenidos anteriores para no perder la base.",
            "Lee los enunciados con atención para mejorar razonamiento e interpretación.",
        ],
    },
    "quimica": {
        "pt-BR": [
            "Entenda conceitos e reações antes de avançar para listas maiores.",
            "Associe teoria com exercícios e revise os erros.",
            "Use mapas mentais para organizar ligações entre temas.",
            "Faça leitura complementar para melhorar compreensão e interpretação.",
        ],
        "en": [
            "Understand concepts and reactions before moving to larger exercise sets.",
            "Connect theory to exercises and review mistakes.",
            "Use mind maps to organize links between topics.",
            "Do complementary reading to improve understanding and interpretation.",
        ],
        "es": [
            "Entiende conceptos y reacciones antes de avanzar a listas más grandes.",
            "Asocia teoría con ejercicios y revisa los errores.",
            "Usa mapas mentales para organizar conexiones entre temas.",
            "Haz lectura complementaria para mejorar comprensión e interpretación.",
        ],
    },
    "biologia": {
        "pt-BR": [
            "Estude por sistemas e processos, não só por memorização solta.",
            "Use esquemas, diagramas e resumos com suas próprias palavras.",
            "Revise conceitos com frequência para aumentar retenção.",
            "Faça leitura complementar para melhorar interpretação dos conteúdos.",
        ],
        "en": [
            "Study by systems and processes, not only by isolated memorization.",
            "Use diagrams and summaries in your own words.",
            "Review concepts often to improve retention.",
            "Do complementary reading to improve content interpretation.",
        ],
        "es": [
            "Estudia por sistemas y procesos, no solo con memorización aislada.",
            "Usa esquemas, diagramas y resúmenes con tus propias palabras.",
            "Revisa conceptos con frecuencia para mejorar la retención.",
            "Haz lectura complementaria para mejorar la interpretación del contenido.",
        ],
    },
}


def normalize_text(text: str) -> str:
    no_accents = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    lowered = no_accents.lower()
    return re.sub(r"[^a-z0-9\s]", " ", lowered).strip()


def detect_subject(message: str) -> str | None:
    normalized = normalize_text(message)
    tokens = set(normalized.split())
    for subject, aliases in SUBJECT_ALIASES.items():
        normalized_aliases = {normalize_text(alias) for alias in aliases}
        if tokens.intersection(normalized_aliases):
            return subject
        if any(alias in normalized for alias in normalized_aliases):
            return subject
    if "nao consigo aprender fisica" in normalized:
        return "fisica"
    if "nao to entendendo quimica" in normalized:
        return "quimica"
    return None


def detect_intent(message: str) -> str:
    normalized = normalize_text(message)
    if any(fragment in normalized for fragment in {"como estudar", "como aprender", "me ajuda", "dificuldade", "nao consigo", "nao entendo"}):
        return "study_guidance"
    return "unknown"


def _subject_label(subject: str, language_code: str) -> str:
    return localized_text(language_code, SUBJECT_LABELS[subject])


def _consistency_state(user, institution_id: int) -> str:
    week_sessions = StudySession.objects.filter(
        student=user,
        institution_id=institution_id,
        created_at__date__gte=timezone.localdate() - timedelta(days=6),
    ).count()
    score = latest_score(user, institution_id)
    if score is None:
        score_data = calculate_score_payload(user, institution_id)
        score_value = score_data["score_value"]
    else:
        score_value = score.score_value

    if score_value <= 500 or week_sessions <= 2:
        return "low"
    if score_value >= 701 or week_sessions >= 5:
        return "high"
    return "medium"


def _habit_guidance(language_code: str, consistency_state: str) -> str:
    if consistency_state == "low":
        return localized_text(
            language_code,
            {
                "pt-BR": "Percebi que sua consistência de estudo está baixa. Tente começar com sessões curtas de 25 minutos, faça uma pausa de 5 minutos e repita.",
                "en": "Your study consistency seems low. Start with 25-minute sessions, take a 5-minute break, and repeat.",
                "es": "Tu consistencia de estudio parece baja. Empieza con sesiones de 25 minutos, haz una pausa de 5 minutos y repite.",
            },
        )
    if consistency_state == "high":
        return localized_text(
            language_code,
            {
                "pt-BR": "Sua consistência está boa. Vale aumentar gradualmente o desafio e revisar conteúdos antigos para aprofundar.",
                "en": "Your consistency is good. Increase the challenge gradually and revisit older topics to go deeper.",
                "es": "Tu consistencia es buena. Vale la pena aumentar gradualmente el desafío y revisar contenidos anteriores para profundizar.",
            },
        )
    return localized_text(
        language_code,
        {
            "pt-BR": "Mantenha rotina estável e distribua o estudo ao longo da semana para ganhar consistência.",
            "en": "Keep a stable routine and spread study across the week to improve consistency.",
            "es": "Mantén una rutina estable y distribuye el estudio durante la semana para mejorar la consistencia.",
        },
    )


def _error_review_guidance(language_code: str) -> str:
    return localized_text(
        language_code,
        {
            "pt-BR": "Refaça os exercícios que você errou antes. Primeiro consulte a solução ou o conteúdo para entender o erro. Depois tente resolver novamente sem consultar.",
            "en": "Redo the exercises you missed. First check the solution or the content to understand the mistake. Then solve them again without checking.",
            "es": "Rehaz los ejercicios que fallaste. Primero revisa la solución o el contenido para entender el error. Después resuélvelos de nuevo sin consultar.",
        },
    )


def answer_study_question(user, message: str, institution_id: int | None = None) -> dict:
    language_code = get_user_language(user)
    institution_id = institution_id or user.institution_id
    subject = detect_subject(message)
    intent = detect_intent(message)

    if subject is None:
        fallback_message = localized_text(
            language_code,
            {
                "pt-BR": "Posso te orientar sobre como estudar melhor Matemática, Português, Física, Química ou Biologia. Diga a disciplina e a dificuldade.",
                "en": "I can guide you on how to study Math, Portuguese, Physics, Chemistry, or Biology better. Tell me the subject and difficulty.",
                "es": "Puedo orientarte sobre cómo estudiar mejor Matemáticas, Portugués, Física, Química o Biología. Dime la materia y la dificultad.",
            },
        )
        return {
            "intent": intent,
            "subject": None,
            "language": language_code,
            "message": fallback_message,
        }

    consistency_state = _consistency_state(user, institution_id) if institution_id else "medium"
    guidance_lines = SUBJECT_GUIDANCE[subject][language_code]
    intro = localized_text(
        language_code,
        {
            "pt-BR": f"Para aprender {_subject_label(subject, language_code)} melhor, foque em uma rotina simples e consistente:",
            "en": f"To learn {_subject_label(subject, language_code)} better, focus on a simple and consistent routine:",
            "es": f"Para aprender {_subject_label(subject, language_code)} mejor, enfócate en una rutina simple y constante:",
        },
    )
    body = " ".join(guidance_lines[:3])
    habit = _habit_guidance(language_code, consistency_state)
    errors = _error_review_guidance(language_code)
    closing = localized_text(
        language_code,
        {
            "pt-BR": "Eu posso te orientar no método de estudo, mas não vou resolver o exercício por você.",
            "en": "I can guide your study method, but I will not solve the exercise for you.",
            "es": "Puedo orientarte en el método de estudio, pero no voy a resolver el ejercicio por ti.",
        },
    )
    return {
        "intent": intent,
        "subject": subject,
        "language": language_code,
        "message": f"{intro} {body} {errors} {habit} {closing}",
    }
