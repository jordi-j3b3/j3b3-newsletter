"""
Cliente mínimo para la API de Brevo (antes Sendinblue).

Base URL: https://api.brevo.com/v3
Documentación: https://developers.brevo.com/

Autenticación: header `api-key: {BREVO_API_KEY}`.

Endpoints usados:
- POST /emailCampaigns                  Crear campaña (borrador)
- POST /emailCampaigns/{id}/sendNow     Enviar inmediatamente
- POST /emailCampaigns/{id}/sendTest    Enviar prueba a direcciones concretas

Migrado desde mailerlite.py el 2026-05-25 (MailerLite Free dejó de permitir
enviar HTML vía API). Este módulo es el único punto de modificación si la API
de Brevo cambia.
"""
from __future__ import annotations

import os
import sys

import requests

BASE_URL = "https://api.brevo.com/v3"


def _session() -> requests.Session:
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY no está definido en config/.env")
    s = requests.Session()
    s.headers.update({
        "api-key": api_key,
        "content-type": "application/json",
        "accept": "application/json",
    })
    return s


def _raise_for_status(r: requests.Response, contexto: str) -> None:
    if r.ok:
        return
    print(f"\nError Brevo ({contexto}): HTTP {r.status_code}", file=sys.stderr)
    print(f"Respuesta: {r.text[:500]}", file=sys.stderr)
    r.raise_for_status()


def create_campaign(
    *,
    name: str,
    subject: str,
    preheader: str,
    from_email: str,
    from_name: str,
    list_ids: list,
    html_content: str,
) -> str:
    """Crea una campaña de email (borrador). Devuelve el campaignId (str).

    `preheader` se mapea al campo `header` de la campaña. `list_ids` son los
    IDs numéricos de las listas destinatarias.
    """
    s = _session()
    payload = {
        "name": name,
        "subject": subject,
        "htmlContent": html_content,
        "sender": {"name": from_name, "email": from_email},
        "recipients": {"listIds": [int(x) for x in list_ids]},
        "header": preheader,
    }
    r = s.post(f"{BASE_URL}/emailCampaigns", json=payload, timeout=30)
    _raise_for_status(r, "crear campaña")
    campaign_id = r.json().get("id")
    if not campaign_id:
        raise RuntimeError(f"Respuesta inesperada al crear campaña: {r.text[:300]}")
    return str(campaign_id)


def send_campaign(campaign_id: str) -> dict:
    """Envía la campaña inmediatamente (POST sendNow). Brevo responde 204."""
    s = _session()
    r = s.post(f"{BASE_URL}/emailCampaigns/{campaign_id}/sendNow", timeout=30)
    _raise_for_status(r, f"enviar campaña {campaign_id}")
    return {"campaign_id": campaign_id, "status_code": r.status_code}


def send_test(
    *,
    email,
    subject: str,
    html_content: str,
    from_email: str,
    from_name: str,
    preheader: str = "",
    name: str | None = None,
    list_ids: list | None = None,
) -> dict:
    """Crea una campaña borrador y le envía una prueba a `email`.

    `email` puede ser una dirección o una lista de direcciones. Si no se pasan
    `list_ids`, se usa BREVO_LIST_PREVIEW_ID (Brevo exige una lista destinataria
    al crear la campaña, aunque la prueba va a las direcciones de `email`).
    """
    if list_ids is None:
        lid = os.environ.get("BREVO_LIST_PREVIEW_ID")
        list_ids = [lid] if lid else []
    name = name or f"[TEST] {subject[:50]}"
    campaign_id = create_campaign(
        name=name,
        subject=subject,
        preheader=preheader,
        from_email=from_email,
        from_name=from_name,
        list_ids=list_ids,
        html_content=html_content,
    )
    s = _session()
    addrs = [email] if isinstance(email, str) else list(email)
    r = s.post(
        f"{BASE_URL}/emailCampaigns/{campaign_id}/sendTest",
        json={"emailTo": addrs},
        timeout=30,
    )
    _raise_for_status(r, f"enviar prueba campaña {campaign_id}")
    return {"campaign_id": campaign_id, "status_code": r.status_code}
