"""
Cancel·la una campanya programada a Brevo.

Llegeix el `brevo_campaign_id` del historial_editorial.json per a la setmana
indicada i desprograma la campanya via PUT /v3/emailCampaigns/{id}/status amb
status "suspended". Imprimeix confirmacio i envia notificacio a jordi@j3b3.com.

Nota Brevo (verificat 2026-06-03 contra l'API real, no fiar-se de la doc):
una campanya en estat "queued"/"scheduled" NOMES accepta "suspended" per
desprogramar-la (HTTP 204). Tant "draft" com "cancel" retornen HTTP 400
("X is an invalid status for scheduled campaign"), tot i que la doc oficial
els llista a l'enum. "suspended" treu la campanya de la cua i Brevo no
l'envia; scheduledAt es mante pero no es dispara.

Important: NO toca el mirall al dashboard (si el mirall ja s'ha fet, el
contingut continua visible a la web fins que es revertesqui el commit a ma).

Us:
    python scripts/cancel.py --semana 2026-06-08
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brevo import _session  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"
NOTIFICATION_TO = "jordi@j3b3.com"


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--semana", required=True, help="YYYY-MM-DD del dilluns d'enviament")
    args = p.parse_args()

    if not HISTORIAL_PATH.exists():
        print(f"Error: no existeix {HISTORIAL_PATH}", file=sys.stderr)
        return 1

    historial = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
    candidates = [
        e for e in historial
        if e.get("semana") == args.semana and e.get("brevo_campaign_id")
    ]
    if not candidates:
        print(
            f"Error: cap entrada amb semana={args.semana} i brevo_campaign_id al historial",
            file=sys.stderr,
        )
        return 1

    entry = candidates[-1]
    campaign_id = entry["brevo_campaign_id"]
    numero = entry.get("numero", "?")

    print(f"Cancel·lant Núm. {numero} · setmana {args.semana} · campaign {campaign_id}…")

    s = _session()
    r = s.put(
        f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/status",
        json={"status": "suspended"},
        timeout=30,
    )
    if not r.ok:
        print(f"Error Brevo: HTTP {r.status_code}", file=sys.stderr)
        print(f"Respuesta: {r.text[:500]}", file=sys.stderr)
        return 2

    print(f"Campanya {campaign_id} suspesa (status=suspended). Brevo no l'enviara dilluns.")

    entry["cancelled_at_utc"] = datetime.now(timezone.utc).isoformat()
    HISTORIAL_PATH.write_text(
        json.dumps(historial, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    from_email = os.environ.get("BREVO_FROM_EMAIL")
    from_name = os.environ.get("BREVO_FROM_NAME", "Observatorio del Comercio")
    if from_email:
        notif_payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": NOTIFICATION_TO}],
            "subject": f"[OBSERVATORI] Núm. {numero} CANCEL·LAT",
            "htmlContent": (
                f"<h2 style='font-family:sans-serif'>Newsletter cancel·lada</h2>"
                f"<p><strong>Núm. {numero}</strong> · setmana {args.semana}</p>"
                f"<p>La campanya s'ha suspes (status=suspended). Brevo NO l'enviara dilluns.</p>"
                f"<p style='color:#888;font-size:0.85em'>Campaign ID: {campaign_id}</p>"
                f"<hr>"
                f"<p style='color:#c0392b'><strong>Atencio:</strong> si el mirall al "
                f"dashboard ja s'ha publicat, el contingut continua visible a la web. "
                f"Reverteix el commit corresponent a observatori-comerc si vols treure'l.</p>"
            ),
        }
        notif = s.post(
            "https://api.brevo.com/v3/smtp/email", json=notif_payload, timeout=30,
        )
        if notif.ok:
            print(f"Notificacio enviada a {NOTIFICATION_TO}")
        else:
            print(f"Avis: no s'ha pogut enviar la notificacio (HTTP {notif.status_code})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
