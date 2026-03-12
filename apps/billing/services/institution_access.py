from __future__ import annotations

from datetime import date
from typing import Optional

from django.db.models import QuerySet

from billing.models import Institution, InstitutionSubscription


def _plan_is_active(subscription: InstitutionSubscription) -> bool:
    plan = subscription.plan
    if not plan:
        return False
    # Compatibilidade com código legado: alguns pontos do sistema ainda usam `is_active`.
    # O campo canônico legado continua valendo enquanto não migramos tudo para `active`.
    return bool(getattr(plan, "is_active", True))


def _subscription_window_is_valid(subscription: InstitutionSubscription, at: Optional[date] = None) -> bool:
    today = at or date.today()
    if subscription.status != InstitutionSubscription.STATUS_ACTIVE:
        return False
    if subscription.start_date and subscription.start_date > today:
        return False
    if subscription.end_date and subscription.end_date < today:
        return False
    return True


def is_institution_subscription_valid(institution: Optional[Institution], at: Optional[date] = None) -> bool:
    """
    Valida se a instituição pode acessar o sistema no momento.
    A regra atual verifica:
    - assinatura com status ativo;
    - data final coerente;
    - plano canônico ativo.
    """
    if institution is None:
        return False
    if not institution.ativa:
        return False

    latest_subscription: Optional[InstitutionSubscription] = (
        InstitutionSubscription.objects.filter(institution=institution)
        .select_related("plan")
        .order_by("-start_date", "-id")
        .first()
    )
    if latest_subscription is None:
        return False

    return _subscription_window_is_valid(latest_subscription, at=at) and _plan_is_active(latest_subscription)


def get_institution_subscription(institution: Institution) -> Optional[InstitutionSubscription]:
    """
    Retorna a assinatura mais recente para decisões de UI/admin.
    Mantém previsibilidade para exibição sem gerar múltiplas queries.
    """
    return InstitutionSubscription.objects.filter(institution=institution).order_by("-start_date", "-id").first()


def user_has_institutional_access(user) -> bool:
    """
    Regra de acesso institucional para o login/perfil do usuário.
    Usuários sem instituição vinculada retornam falso.
    """
    if user is None:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return is_institution_subscription_valid(getattr(user, "institution", None))


def active_institution_subscriptions_for(institution: Institution) -> QuerySet[InstitutionSubscription]:
    """
    Helpers utilitário para relatórios e auditoria.
    """
    return InstitutionSubscription.objects.filter(institution=institution).select_related("plan")
