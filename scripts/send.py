"""
Envía la newsletter al grupo destino tras doble confirmación explícita.

NORMA CRÍTICA: nunca se ejecuta el envío sin que el usuario haya escrito
'sí' al menos dos veces en el terminal.

Lee:
- output/semana-YYYY-MM-DD/newsletter.html
- output/semana-YYYY-MM-DD/newsletter.md

Escribe:
- output/semana-YYYY-MM-DD/send_log.json

Uso:
    python scripts/send.py --semana 2026-05-19 --numero 1
    python scripts/send.py --semana 2026-05-19 --numero 1 --grupo MAILERLITE_GROUP_GRATUITA_ID
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mailerlite import create_campaign, schedule_campaign_now  # noqa: E402
from compose import extraer_meta, strip_trazabilidad  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)


def confirmar(pregunta: str) -> bool:
    while True:
        resp = input(f"{pregunta} (s/N): ").strip().lower()
        if resp in ("s", "si", "sí"):
            return True
        if resp in ("", "n", "no"):
            return False
        print("Respuesta no reconocida. Escribe 's' o 'n'.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", required=True)
    p.add_argument("--numero", type=int, required=True)
    p.add_argument(
        "--grupo",
        default="MAILERLITE_GROUP_PILOT_ID",
        help="Nombre de la variable de entorno con el ID del grupo destino "
             "(default: MAILERLITE_GROUP_PILOT_ID)",
    )
    args = p.parse_args()

    week_dir = ROOT / "output" / f"semana-{args.semana}"
    html_path = week_dir / "newsletter.html"
    md_path = week_dir / "newsletter.md"

    if not html_path.exists():
        print(f"Error: no existe {html_path}", file=sys.stderr)
        return 1

    md_text = strip_trazabilidad(md_path.read_text(encoding="utf-8"))
    meta = extraer_meta(md_text)
    subject = meta["subject"]
    preheader = meta["preheader"]
    html = html_path.read_text(encoding="utf-8")

    group_id = os.environ.get(args.grupo)
    if not group_id:
        print(f"Error: {args.grupo} no está definido en config/.env", file=sys.stderr)
        return 2
    from_email = os.environ.get("MAILERLITE_FROM_EMAIL")
    if not from_email:
        print("Error: MAILERLITE_FROM_EMAIL no está definido en config/.env", file=sys.stderr)
        return 2
    from_name = os.environ.get("MAILERLITE_FROM_NAME", "Observatorio del Comercio")
    modo = os.environ.get("MODO_EJECUCION", "prueba")

    print()
    print("=" * 60)
    print(f"  ENVÍO REAL — Núm. {args.numero}")
    print("=" * 60)
    print(f"  Semana:    {args.semana}")
    print(f"  Asunto:    {subject}")
    print(f"  Preheader: {preheader}")
    print(f"  Remitente: {from_name} <{from_email}>")
    print(f"  Grupo:     {args.grupo} (ID: {group_id})")
    print(f"  Modo:      {modo}")
    print()
    if not confirmar("¿Has revisado la preview en tu correo y la das por buena?"):
        print("Cancelado. No se ha enviado nada.")
        return 0
    if not confirmar(f"CONFIRMACIÓN FINAL: ¿enviar a {args.grupo} AHORA?"):
        print("Cancelado. No se ha enviado nada.")
        return 0

    name = f"Núm. {args.numero} · semana {args.semana}"
    print(f"\nCreando campaña: {name}")
    campaign_id = create_campaign(
        name=name,
        subject=subject,
        preheader=preheader,
        from_email=from_email,
        from_name=from_name,
        group_ids=[group_id],
        html=html,
    )
    print(f"  Campaign ID: {campaign_id}")
    print("Encolando envío inmediato...")
    schedule_campaign_now(campaign_id)
    print("Envío encolado.")

    log = {
        "envio_utc": datetime.now(timezone.utc).isoformat(),
        "semana": args.semana,
        "numero": args.numero,
        "asunto": subject,
        "preheader": preheader,
        "remitente": {"nombre": from_name, "email": from_email},
        "grupo_variable": args.grupo,
        "grupo_id": group_id,
        "campaign_id": campaign_id,
        "modo": modo,
    }
    log_path = week_dir / "send_log.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Envío registrado en {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
