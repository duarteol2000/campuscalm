import os
from typing import Dict

from utils.constants import (
    FEATURE_COACH_ADVANCED,
    FEATURE_EMAIL_NOTIFICATIONS,
    FEATURE_REPORTS_ADVANCED,
    FEATURE_SMS,
    FEATURE_WHATSAPP,
    PLAN_LITE,
    PLAN_PRO,
    REQUESTER_INSTITUTION,
)

TRIAGE_MODEL_NAME = os.getenv("TRIAGE_MODEL_NAME", "mock-v1")
TRIAGE_USE_LLM = os.getenv("TRIAGE_USE_LLM", "false").lower() == "true"


def rule_based_plan(access_request) -> str:
    if access_request.requester_type == REQUESTER_INSTITUTION:
        return PLAN_PRO
    if access_request.estimated_users and access_request.estimated_users >= 50:
        return PLAN_PRO
    wants = set(access_request.wants_features or [])
    pro_features = {
        FEATURE_REPORTS_ADVANCED,
        FEATURE_EMAIL_NOTIFICATIONS,
        FEATURE_WHATSAPP,
        FEATURE_SMS,
        FEATURE_COACH_ADVANCED,
    }
    if wants.intersection(pro_features):
        return PLAN_PRO
    return PLAN_LITE


def mock_ai_output(recommended_plan: str) -> Dict[str, object]:
    if recommended_plan == PLAN_PRO:
        score = 82
        rationale = "Solicitacao com sinais de necessidade avancada."
    else:
        score = 28
        rationale = "Solicitacao adequada ao plano basico."
    return {
        "score": score,
        "recommended_plan": recommended_plan,
        "rationale": rationale,
        "llm_enabled": TRIAGE_USE_LLM,
    }


def run_triage(access_request) -> Dict[str, object]:
    recommended_plan = rule_based_plan(access_request)
    output = mock_ai_output(recommended_plan)
    return {
        "recommended_plan": recommended_plan,
        "output_payload": output,
    }
