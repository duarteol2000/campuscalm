from typing import Optional

from rest_framework.exceptions import PermissionDenied

from billing.models import Plan, UserSubscription
from utils.constants import PLAN_LITE


def get_user_plan(user) -> Optional[Plan]:
    if not user or not getattr(user, "is_authenticated", False):
        return None
    subscription = (
        UserSubscription.objects.filter(user=user, is_active=True)
        .select_related("plan")
        .first()
    )
    if subscription and subscription.plan and subscription.plan.is_active:
        return subscription.plan
    return Plan.objects.filter(code=PLAN_LITE, is_active=True).first()


def has_feature(user, feature_name: str) -> bool:
    plan = get_user_plan(user)
    if not plan or plan.features is None:
        return False
    if isinstance(plan.features, list):
        return feature_name in plan.features
    if isinstance(plan.features, dict):
        return bool(plan.features.get(feature_name))
    return False


def require_feature(user, feature_name: str, message: Optional[str] = None) -> None:
    if not has_feature(user, feature_name):
        raise PermissionDenied(message or "Seu plano atual nao permite este recurso.")
