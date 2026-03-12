from __future__ import annotations

from django.utils import translation


LANGUAGE_PT_BR = "pt-BR"
LANGUAGE_EN = "en"
LANGUAGE_ES = "es"

_PREFERRED_TO_DJANGO = {
    LANGUAGE_PT_BR: "pt-br",
    "pt-br": "pt-br",
    LANGUAGE_EN: "en",
    LANGUAGE_ES: "es",
}


def normalize_preferred_language(language_code: str | None) -> str:
    if not language_code:
        return LANGUAGE_PT_BR
    return language_code if language_code in {LANGUAGE_PT_BR, LANGUAGE_EN, LANGUAGE_ES} else LANGUAGE_PT_BR


def to_django_language(language_code: str | None) -> str:
    preferred = normalize_preferred_language(language_code)
    return _PREFERRED_TO_DJANGO.get(preferred, "pt-br")


def get_user_language(user) -> str:
    return normalize_preferred_language(getattr(user, "preferred_language", LANGUAGE_PT_BR))


def activate_language(language_code: str | None) -> str:
    django_code = to_django_language(language_code)
    translation.activate(django_code)
    return django_code


def localized_text(language_code: str | None, translations: dict[str, str], fallback: str = LANGUAGE_PT_BR) -> str:
    preferred = normalize_preferred_language(language_code)
    if preferred in translations:
        return translations[preferred]
    if fallback in translations:
        return translations[fallback]
    return next(iter(translations.values()))
