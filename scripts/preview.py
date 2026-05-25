"""
Envía la newsletter actual a la lista BREVO_LIST_PREVIEW_ID (Brevo).

La lista preview contiene una sola dirección. El envío es silencioso: no
requiere confirmación, ya que el objetivo es precisamente comprobar el
renderizado real vía la misma API que el envío de producción.

Lee:
- output/semana-YYYY-MM-DD/newsletter.html
- output/semana-YYYY-MM-DD/newsletter.md  (para extraer asunto/preheader)

Uso:
    python scripts/preview.py --semana 2026-05-19 --numero 1
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brevo import create_campaign, send_campaign  # noqa: E402
from compose import extraer_meta, strip_trazabilidad  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", required=True)
    p.add_argument("--numero", type=int, required=True)
    args = p.parse_args()

    week_dir = ROOT / "output" / f"semana-{args.semana}"
    html_path = week_dir / "newsletter.html"
    md_path = week_dir / "newsletter.md"

    if not html_path.exists():
        print(f"Error: no existe {html_path}. Ejecuta scripts/compose.py primero.", file=sys.stderr)
        return 1

    md_text = strip_trazabilidad(md_path.read_text(encoding="utf-8"))
    meta = extraer_meta(md_text)
    subject = meta["subject"]
    preheader = meta["preheader"]
    html = html_path.read_text(encoding="utf-8")

    list_id = os.environ.get("BREVO_LIST_PREVIEW_ID")
    if not list_id:
        print("Error: BREVO_LIST_PREVIEW_ID no está definido en config/.env", file=sys.stderr)
        return 2
    from_email = os.environ.get("BREVO_FROM_EMAIL")
    if not from_email:
        print("Error: BREVO_FROM_EMAIL no está definido en config/.env", file=sys.stderr)
        return 2
    from_name = os.environ.get("BREVO_FROM_NAME", "Observatorio del Comercio")
    destino = os.environ.get("EMAIL_PREVIEW", "jordi@j3b3.com")

    name = f"[PREVIEW] Núm. {args.numero} · semana {args.semana}"
    print(f"Creando campaña preview: {name}")
    campaign_id = create_campaign(
        name=name,
        subject=f"[PREVIEW] {subject}",
        preheader=preheader,
        from_email=from_email,
        from_name=from_name,
        list_ids=[list_id],
        html_content=html,
    )
    print(f"  Campaign ID: {campaign_id}")
    print("Enviando inmediatamente...")
    send_campaign(campaign_id)
    print(f"Preview enviada. Revisa la bandeja de {destino}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
