import json
import re
import urllib.request
from typing import Dict

from django.conf import settings


# Bloco: Normalizacao de telefone
def normalize_phone(raw_phone: str) -> str:
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("55"):
        return digits
    return f"55{digits}"


# Bloco: Envio de mensagem via WhatsApp Cloud API
def send_whatsapp_text(to_phone: str, body: str) -> Dict:
    token = getattr(settings, "WHATSAPP_CLOUD_TOKEN", "")
    phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_number_id:
        raise RuntimeError("Credenciais do WhatsApp Cloud nao configuradas.")

    normalized = normalize_phone(to_phone)
    if not normalized:
        raise RuntimeError("Telefone invalido para envio de WhatsApp.")

    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized,
        "type": "text",
        "text": {"body": body},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Erro ao enviar WhatsApp: {exc}") from exc
