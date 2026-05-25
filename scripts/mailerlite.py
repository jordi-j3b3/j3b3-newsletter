"""
Cliente mínimo para la API de MailerLite (Connect / v2 actual).

Base URL: https://connect.mailerlite.com/api
Documentación: https://developers.mailerlite.com/docs/

Endpoints usados:
- POST   /api/campaigns                  Crear borrador de campaña
- POST   /api/campaigns/{id}/schedule    Programar envío (delivery=instant)
- GET    /api/campaigns/{id}             Estado de la campaña

Si la API cambia o falla con la forma actual, este módulo es el único punto
de modificación.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Optional

import requests

BASE_URL = "https://connect.mailerlite.com/api"


def _session() -> requests.Session:
    token = os.environ.get("MAILERLITE_API_TOKEN")
    if not token:
        raise RuntimeError("MAILERLITE_API_TOKEN no está definido en config/.env")
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    return s


def _raise_for_status(r: requests.Response, contexto: str) -> None:
    if r.ok:
        return
    cuerpo = r.text[:500]
    print(f"\nError MailerLite ({contexto}): HTTP {r.status_code}", file=sys.stderr)
    print(f"Respuesta: {cuerpo}", file=sys.stderr)
    r.raise_for_status()


def _html_to_plain(html: str) -> str:
    """Conversión mínima HTML → texto plano para el campo plain_text."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def create_campaign(
    *,
    name: str,
    subject: str,
    preheader: str,
    from_email: str,
    from_name: str,
    group_ids: list[str],
    html: str,
    plain_text: Optional[str] = None,
) -> str:
    """Crea un borrador de campaña tipo 'regular'. Devuelve el ID.

    El campo 'emails' es un array de objetos. Para campañas 'regular' contiene
    un único objeto con los campos requeridos: subject, from_name, from.

    No se envía 'plain_text' (no es campo aceptado por el endpoint actual).
    MailerLite genera la versión plain text automáticamente desde el HTML.
    """
    s = _session()
    email_obj = {
        "subject": subject,
        "from_name": from_name,
        "from": from_email,
        "content": html,
    }
    payload = {
        "name": name,
        "type": "regular",
        "emails": [email_obj],
        "groups": [str(g) for g in group_ids],
    }
    r = s.post(f"{BASE_URL}/campaigns", json=payload, timeout=30)
    _raise_for_status(r, "crear campaña")
    data = r.json().get("data", {})
    campaign_id = data.get("id")
    if not campaign_id:
        raise RuntimeError(f"Respuesta inesperada al crear campaña: {r.text[:300]}")
    return str(campaign_id)


def schedule_campaign_now(campaign_id: str) -> dict:
    """Encola la campaña para envío inmediato."""
    s = _session()
    payload = {"delivery": "instant"}
    r = s.post(
        f"{BASE_URL}/campaigns/{campaign_id}/schedule",
        json=payload,
        timeout=30,
    )
    _raise_for_status(r, f"schedule campaña {campaign_id}")
    return r.json()


def get_campaign(campaign_id: str) -> dict:
    s = _session()
    r = s.get(f"{BASE_URL}/campaigns/{campaign_id}", timeout=30)
    _raise_for_status(r, f"obtener campaña {campaign_id}")
    return r.json()
