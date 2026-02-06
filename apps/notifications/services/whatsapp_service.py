import logging
import re
from typing import Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# Bloco: Normalizacao de telefone
def normalize_phone(raw_phone: str) -> str:
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("55"):
        return digits
    return f"55{digits}"


# Bloco: Envio de mensagem WhatsApp (retorna resposta)
def send_whatsapp_message_raw(phone_number: str, message: str) -> Optional[Dict]:
    token = getattr(settings, "WHATSAPP_CLOUD_TOKEN", "")
    phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_number_id:
        logger.error("Credenciais do WhatsApp Cloud nao configuradas.")
        return None

    normalized = normalize_phone(phone_number)
    if not normalized:
        logger.error("Telefone invalido para envio de WhatsApp.")
        return None

    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized,
        "type": "text",
        "text": {"body": message},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code >= 400:
            logger.error("Erro WhatsApp Cloud %s: %s", response.status_code, response.text)
            return None
        return response.json()
    except requests.RequestException as exc:
        logger.exception("Erro ao enviar WhatsApp: %s", exc)
        return None


# Bloco: Envio de mensagem WhatsApp (retorna sucesso)
def send_whatsapp_message(phone_number: str, message: str) -> bool:
    return send_whatsapp_message_raw(phone_number, message) is not None
