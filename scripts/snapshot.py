"""
Captura snapshot semanal de datos del Observatorio del Comercio.

Genera data/semana-YYYY-MM-DD/ con:
  - pulso_diario.csv        copia íntegra de cdmge.csv
  - pulso_europeo.csv       copia íntegra de europa_retail_mensual.csv
  - recopilacion_prensa.md  serializado de modules.press.fetch_press(),
                            filtrado a la ventana configurada
  - _meta.json              metadatos de la captura

El snapshot se congela una vez generado. Para regenerarlo, usar --force
(rompe la trazabilidad; reservado para correcciones, no para uso normal).

Uso:
    python scripts/snapshot.py                  # próximo lunes
    python scripts/snapshot.py --semana 2026-05-19
    python scripts/snapshot.py --semana 2026-05-19 --force
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)


def next_monday(today: datetime | None = None) -> datetime:
    """Devuelve el próximo lunes de envío.

    Si hoy es lunes antes de las 09:00, se asume que ese mismo lunes es
    el día de envío. En cualquier otro momento, devuelve el lunes
    siguiente.
    """
    today = today or datetime.now()
    weekday = today.weekday()  # 0 = lunes
    if weekday == 0 and today.hour < 9:
        return today.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = (7 - weekday) % 7 or 7
    return (today + timedelta(days=delta)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--semana",
        help="Fecha del lunes de envío (YYYY-MM-DD). Por defecto, próximo lunes.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribir snapshot existente. Rompe la trazabilidad. Solo para correcciones.",
    )
    return p.parse_args()


def copy_csv(src: Path, dst: Path, label: str) -> dict:
    if not src.exists():
        raise FileNotFoundError(f"No se encuentra la fuente de {label}: {src}")
    shutil.copy2(src, dst)
    df = pd.read_csv(dst)
    return {"origen": str(src), "filas": len(df)}


def cdmge_meta(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path, parse_dates=["data"])
    ultima = df["data"].max()
    lag_dias = (datetime.now() - ultima.to_pydatetime()).days
    return {
        "ultima_fecha": ultima.strftime("%Y-%m-%d"),
        "lag_dias": lag_dias,
    }


def europa_meta(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    ultimo = df["periode"].max()  # formato YYYY-MM
    year, month = map(int, ultimo.split("-"))
    # Aproximamos la fecha del periodo al último día del mes informado.
    if month == 12:
        first_next = datetime(year + 1, 1, 1)
    else:
        first_next = datetime(year, month + 1, 1)
    fin_mes = first_next - timedelta(days=1)
    lag_dias = (datetime.now() - fin_mes).days
    return {"ultimo_periodo": ultimo, "lag_dias": lag_dias}


def capture_press(out_md: Path, observatori_path: Path, dias: int) -> dict:
    """Llama a modules.press.fetch_press() del Observatorio y serializa
    los items de los últimos `dias` días a markdown legible."""
    obs_path_str = str(observatori_path)
    if obs_path_str not in sys.path:
        sys.path.insert(0, obs_path_str)
    try:
        from modules.press import fetch_press, FEEDS  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            f"No se puede importar modules.press desde {observatori_path}. "
            f"Verificar OBSERVATORI_PATH en config/.env. Error: {e}"
        )

    df = fetch_press()
    feeds_total = len(FEEDS)
    captura_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if df.empty:
        out_md.write_text(
            f"# Recopilación de prensa\n\n"
            f"Captura: {captura_iso}\n\n"
            f"Sin entradas en ningún feed. Revisar conectividad o feeds caídos antes de generar el borrador.\n",
            encoding="utf-8",
        )
        return {"feeds_ok": 0, "feeds_fallidos": [f[0] for f in FEEDS], "items": 0, "ventana_dias": dias}

    cutoff = datetime.now(timezone.utc) - timedelta(days=dias)
    df["data"] = pd.to_datetime(df["data"], utc=True, errors="coerce")
    df = df[df["data"] >= cutoff].sort_values("data", ascending=False).reset_index(drop=True)

    feeds_presentes = set(df["font_id"].unique())
    feeds_ok = len(feeds_presentes)
    feeds_fallidos = [f[0] for f in FEEDS if f[0] not in feeds_presentes]

    lines = [
        "# Recopilación de prensa",
        "",
        f"Captura: {captura_iso} · {feeds_ok}/{feeds_total} feeds con entradas en la ventana",
    ]
    if feeds_fallidos:
        lines.append(f"Feeds sin entradas en la ventana: {', '.join(feeds_fallidos)}")
    lines.append(f"Ventana: últimos {dias} días")
    lines.append("")

    fecha_actual = None
    for _, row in df.iterrows():
        fecha = row["data"].strftime("%Y-%m-%d")
        if fecha != fecha_actual:
            lines.append("")
            lines.append(f"## {fecha}")
            lines.append("")
            fecha_actual = fecha
        lines.append(f"### {row['titol']}")
        lines.append(f"- Fuente: {row['font']} ({row['tipus']}, {row['area']}, {row['segment']})")
        snippet = row.get("snippet") or ""
        if snippet:
            lines.append(f"- Snippet: {snippet}")
        lines.append(f"- URL: {row['link']}")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return {
        "feeds_ok": feeds_ok,
        "feeds_fallidos": feeds_fallidos,
        "items": len(df),
        "ventana_dias": dias,
    }


def main() -> int:
    args = parse_args()

    if args.semana:
        try:
            lunes = datetime.strptime(args.semana, "%Y-%m-%d")
        except ValueError:
            print(f"Error: --semana debe ser YYYY-MM-DD, recibido: {args.semana}", file=sys.stderr)
            return 2
    else:
        lunes = next_monday()

    semana_str = lunes.strftime("%Y-%m-%d")
    semana_dir = ROOT / "data" / f"semana-{semana_str}"

    if semana_dir.exists() and not args.force:
        print(f"Error: el snapshot ya existe en {semana_dir}", file=sys.stderr)
        print("Usa --force para sobrescribir. Rompe la trazabilidad: solo para correcciones.", file=sys.stderr)
        return 1

    semana_dir.mkdir(parents=True, exist_ok=True)

    obs_path_raw = os.environ.get("OBSERVATORI_PATH")
    if not obs_path_raw:
        print("Error: OBSERVATORI_PATH no está definido en config/.env", file=sys.stderr)
        return 2
    obs_path = Path(obs_path_raw).expanduser()

    cdmge_src = obs_path / SETTINGS["snapshot"]["cdmge_origen"]
    europa_src = obs_path / SETTINGS["snapshot"]["europa_origen"]

    pulso_diario_dst = semana_dir / "pulso_diario.csv"
    pulso_europeo_dst = semana_dir / "pulso_europeo.csv"
    prensa_dst = semana_dir / "recopilacion_prensa.md"

    print(f"Capturando snapshot para semana del {semana_str}")
    print(f"  Origen Observatorio: {obs_path}")

    cdmge_info = copy_csv(cdmge_src, pulso_diario_dst, "CDMGE")
    cdmge_info.update(cdmge_meta(pulso_diario_dst))
    print(
        f"  pulso_diario.csv     · {cdmge_info['filas']:>6} filas · "
        f"última fecha {cdmge_info['ultima_fecha']} · lag {cdmge_info['lag_dias']}d"
    )

    europa_info = copy_csv(europa_src, pulso_europeo_dst, "Europa retail")
    europa_info.update(europa_meta(pulso_europeo_dst))
    print(
        f"  pulso_europeo.csv    · {europa_info['filas']:>6} filas · "
        f"último periodo {europa_info['ultimo_periodo']} · lag {europa_info['lag_dias']}d"
    )

    prensa_info = capture_press(prensa_dst, obs_path, SETTINGS["prensa"]["dias_ventana"])
    print(
        f"  recopilacion_prensa  · {prensa_info['items']:>6} items · "
        f"{prensa_info['feeds_ok']} feeds con entradas"
    )
    if prensa_info.get("feeds_fallidos"):
        print(f"     feeds sin entradas: {', '.join(prensa_info['feeds_fallidos'])}")

    meta = {
        "semana_iso": lunes.strftime("%G-W%V"),
        "fecha_envio_prevista": semana_str,
        "captura": datetime.now(timezone.utc).isoformat(),
        "pulso_diario": cdmge_info,
        "pulso_europeo": europa_info,
        "prensa": prensa_info,
    }
    (semana_dir / "_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Snapshot completado en {semana_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
