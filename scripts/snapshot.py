"""
Captura snapshot semanal de datos del Observatorio del Comercio.

Genera data/semana-YYYY-MM-DD/ con:
  - pulso_diario.csv        copia íntegra de cdmge.csv
  - pulso_europeo.csv       copia íntegra de europa_retail_mensual.csv
  - pulso_icm.csv           tall de icm.csv (sèrie general nacional + branques)
  - recopilacion_prensa.md  serializado de modules.press.fetch_press(),
                            filtrado a la ventana configurada, con las
                            entradas [EDITOR] de config/noticies_editor.md
                            (si existe) añadidas al final
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
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)

NOTICIES_EDITOR_PATH = ROOT / "config" / "noticies_editor.md"


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


def productivitat_meta(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    return {"ultimo_any": int(df["any"].max())}


def ocupacio_meta(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    return {"ultimo_any": int(df["any"].max())}


def ipc_meta(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    ultimo_any = int(df["any"].max())
    ultimo_mes = int(df[df["any"] == ultimo_any]["mes"].max())
    return {"ultimo_periode": f"{ultimo_any}-{ultimo_mes:02d}"}


def marges_meta(csv_path: Path) -> dict:
    """Metadades del dataset de marges per branca. La clau `verificat` és True
    només si TOTES les files estan verificades contra el PDF original de PATECO;
    generate.py la usa com a gate per activar l'angle editorial de marges."""
    df = pd.read_csv(csv_path)
    verificat = bool(df["verificat"].astype(bool).all()) if "verificat" in df else False
    return {
        "ultimo_any": int(df["any"].max()),
        "n_branques": int(df["cnae"].nunique()),
        "verificat": verificat,
    }


def copy_csv_optional(src: Path, dst: Path, label: str) -> dict | None:
    """Com copy_csv però retorna None (amb avís) si el fitxer no existeix."""
    if not src.exists():
        print(f"  {label}: no trobat a {src}, s'omet del snapshot", file=sys.stderr)
        return None
    return copy_csv(src, dst, label)


# Branca "general" de l'ICM = índex de comerç al detall CNAE 47 complet, que és
# la xifra de titular que publica l'INE. La variant "47 sin 473" exclou les
# estacions de servei (soroll del preu del combustible).
ICM_BRANCA_GENERAL = "Comercio al por menor, excepto de vehículos de motor y motocicletas"
ICM_BRANCA_SIN473 = "Comercio al por menor sin Estaciones de Servicio (47 sin 473)"


def capture_icm(src: Path, dst: Path, meses: int = 24) -> dict | None:
    """Extreu del icm.csv complet (~48k files) el tall que necessita la
    newsletter i el desa a pulso_icm.csv:
      - sèrie general nacional (CNAE 47 i 47-sin-473), preus nominals i
        constants, indicadors index / var_anual / var_mitjana_acum, últims
        `meses` mesos.
      - desglossament per branca del mes més recent (real, var_anual) per
        poder explicar ON es concentra el moviment.
    """
    if not src.exists():
        print(f"  ICM: no trobat a {src}, s'omet del snapshot", file=sys.stderr)
        return None

    df = pd.read_csv(src)
    df = df[df["ambit"] == "nacional"].copy()
    if df.empty:
        print(f"  ICM: sense files nacionals a {src}, s'omet", file=sys.stderr)
        return None

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    periodes = sorted(df["data"].dropna().unique())
    cutoff = periodes[-meses] if len(periodes) >= meses else periodes[0]

    general = df[
        df["branca"].isin([ICM_BRANCA_GENERAL, ICM_BRANCA_SIN473])
        & df["tipus"].isin(["nominal", "real"])
        & df["indicador"].isin(["index", "var_anual", "var_mitjana_acum"])
        & (df["data"] >= cutoff)
    ]

    # Desglossament per branca del mes més recent (real, var_anual)
    ult_data = df["data"].max()
    branques = df[
        (df["tipus"] == "real")
        & (df["indicador"] == "var_anual")
        & (df["data"] == ult_data)
    ]

    out = pd.concat([general, branques]).drop_duplicates()
    cols = ["ambit", "tipus", "branca", "indicador", "any", "mes", "data", "valor"]
    out = out[cols].sort_values(["tipus", "branca", "indicador", "data"])
    out.to_csv(dst, index=False)

    # Metadades: últim periode i valor de titular (general real var_anual)
    gen_real_va = df[
        (df["branca"] == ICM_BRANCA_GENERAL)
        & (df["tipus"] == "real")
        & (df["indicador"] == "var_anual")
    ].sort_values("data")
    ultim = gen_real_va.iloc[-1] if not gen_real_va.empty else None
    ultimo_periodo = ult_data.strftime("%Y-%m") if pd.notna(ult_data) else ""
    lag_dias = (datetime.now() - ult_data.to_pydatetime()).days if pd.notna(ult_data) else None

    return {
        "origen": str(src),
        "filas": len(out),
        "ultimo_periodo": ultimo_periodo,
        "lag_dias": lag_dias,
        "general_real_var_anual": float(ultim["valor"]) if ultim is not None else None,
    }


def capture_icm_distribucio(src: Path, dst: Path, meses: int = 24) -> dict | None:
    """Extreu d'icm_distribucion.csv (4 modes de distribució: Grandes
    Superficies, Grandes cadenas, Pequeñas cadenas, Empresas unilocalizadas)
    el tall que necessita la newsletter: sèrie nominal+real dels últims
    `meses` mesos per als 4 modes, i el desa a pulso_icm_distribucio.csv."""
    if not src.exists():
        print(f"  ICM distribució: no trobat a {src}, s'omet del snapshot", file=sys.stderr)
        return None

    df = pd.read_csv(src)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    periodes = sorted(df["data"].dropna().unique())
    if not periodes:
        print(f"  ICM distribució: sense dates vàlides a {src}, s'omet", file=sys.stderr)
        return None
    cutoff = periodes[-meses] if len(periodes) >= meses else periodes[0]

    out = df[
        df["tipus"].isin(["nominal", "real"])
        & df["indicador"].isin(["index", "var_anual", "var_mitjana_acum"])
        & (df["data"] >= cutoff)
    ]
    cols = ["tipus", "modo", "indicador", "any", "mes", "data", "valor"]
    out = out[cols].sort_values(["tipus", "modo", "indicador", "data"])
    out.to_csv(dst, index=False)

    ult_data = df["data"].max()
    ultimo_periodo = ult_data.strftime("%Y-%m") if pd.notna(ult_data) else ""
    lag_dias = (datetime.now() - ult_data.to_pydatetime()).days if pd.notna(ult_data) else None
    modes_ult = df[
        (df["data"] == ult_data) & (df["tipus"] == "real") & (df["indicador"] == "var_anual")
    ][["modo", "valor"]]

    return {
        "origen": str(src),
        "filas": len(out),
        "ultimo_periodo": ultimo_periodo,
        "lag_dias": lag_dias,
        "modes_real_var_anual": {
            row["modo"]: float(row["valor"]) for _, row in modes_ult.iterrows()
        },
    }


def parse_noticies_editor(path: Path, semana_str: str) -> list[dict]:
    """Parseja config/noticies_editor.md i retorna les entrades de la secció
    '## Setmana YYYY-MM-DD' que coincideix amb `semana_str`. Format esperat:

        ## Setmana 2026-07-13

        - URL: https://exemple.com/noticia
          Angle: ...
          Segment: petit_comerc

    Si el fitxer no existeix o no hi ha secció per a aquesta setmana,
    retorna [] (no s'aplica cap entrada d'una setmana diferent)."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^##\s*Setmana\s+(\S+)\s*$", text, flags=re.MULTILINE)
    entries: list[dict] = []
    for i in range(1, len(sections), 2):
        if sections[i].strip() != semana_str:
            continue
        for bloc_m in re.finditer(
            r"-\s*URL:\s*(\S+)\s*\n\s*Angle:\s*(.+?)\s*\n\s*Segment:\s*(\S+)",
            sections[i + 1],
        ):
            entries.append({
                "url": bloc_m.group(1).strip(),
                "angle": bloc_m.group(2).strip(),
                "segment": bloc_m.group(3).strip(),
            })
    return entries


def fetch_url_titol_paragraf(url: str, timeout: int = 10) -> tuple[str, str] | None:
    """Fa un GET a `url` i n'extreu el <title> i el primer <p> amb text
    substancial (>40 caràcters). Retorna None si el fetch falla (error de
    xarxa o codi HTTP != 200) o si la resposta és 200 però no s'hi pot
    extreure cap <title> — en cap dels dos casos hi ha contingut real per
    citar, i capture_noticies_editor() ha de descartar l'entrada."""
    try:
        resp = requests.get(
            url, timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; J3B3Newsletter/1.0)"},
        )
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as e:
        print(f"  Avís: no s'ha pogut fer fetch de {url} ({e})", file=sys.stderr)
        return None

    titol_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not titol_m:
        print(f"  Avís: fetch de {url} ha tingut èxit (HTTP {resp.status_code}) "
              f"però no s'hi ha trobat cap <title>", file=sys.stderr)
        return None
    titol = re.sub(r"\s+", " ", titol_m.group(1)).strip()

    paragraf = ""
    for p_m in re.finditer(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL):
        candidat = re.sub(r"<[^>]+>", " ", p_m.group(1))
        candidat = re.sub(r"\s+", " ", candidat).strip()
        if len(candidat) > 40:
            paragraf = candidat
            break

    return titol, paragraf


def capture_noticies_editor(
    path: Path, semana_str: str, prensa_md: Path,
) -> tuple[list[dict], list[str]]:
    """Llegeix les entrades de l'editor per a `semana_str`, fa fetch de cada
    URL (títol + primer paràgraf) i afegeix a `prensa_md` (append, ja
    escrit per capture_press) NOMÉS les que tenen contingut real, amb el
    tag [EDITOR] perquè Sonnet les prioritzi. Les URLs que fallen el fetch
    NO s'afegeixen al recull (evita que Sonnet inventi contingut a partir
    només de la URL i l'angle).

    Retorna (capturades, avisos):
      - capturades: entrades amb contingut real (url, titol, angle,
        segment), per desar a _meta.json — generate.py les usa per saber
        quines s'han citat al borrador final i registrar-les a l'historial.
      - avisos: missatges "URL editorial no accessible: ..." per a les que
        han fallat, per al log i la notificació de diumenge (schedule.py)."""
    entries = parse_noticies_editor(path, semana_str)
    if not entries:
        return [], []

    lines = ["", "## Notícies seleccionades per l'editor [EDITOR]", ""]
    capturades = []
    avisos = []
    for e in entries:
        resultat = fetch_url_titol_paragraf(e["url"])
        if resultat is None:
            avis = f"URL editorial no accessible: {e['url']} — no s'ha afegit al recull."
            print(f"  Avís: {avis}", file=sys.stderr)
            avisos.append(avis)
            continue
        titol, snippet = resultat
        capturades.append({
            "url": e["url"], "titol": titol, "angle": e["angle"], "segment": e["segment"],
        })
        lines.append(f"### [EDITOR] {titol}")
        lines.append(f"- Fuente: Selección editorial ({e['segment']})")
        lines.append(f"- Angle editorial: {e['angle']}")
        if snippet:
            lines.append(f"- Snippet: {snippet}")
        lines.append(f"- URL: {e['url']}")
        lines.append("")

    if capturades:
        with prensa_md.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    return capturades, avisos


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
    productivitat_src = obs_path / SETTINGS["snapshot"]["productivitat_origen"]
    ocupacio_src = obs_path / SETTINGS["snapshot"]["ocupacio_origen"]
    ipc_src = obs_path / SETTINGS["snapshot"]["ipc_origen"]
    icm_src = obs_path / SETTINGS["snapshot"]["icm_origen"]
    icm_distribucio_src = obs_path / SETTINGS["snapshot"]["icm_distribucio_origen"]
    marges_src = obs_path / SETTINGS["snapshot"]["marges_origen"]

    pulso_diario_dst = semana_dir / "pulso_diario.csv"
    pulso_europeo_dst = semana_dir / "pulso_europeo.csv"
    productivitat_dst = semana_dir / "productivitat.csv"
    ocupacio_dst = semana_dir / "ocupacio_comerc.csv"
    ipc_dst = semana_dir / "ipc.csv"
    icm_dst = semana_dir / "pulso_icm.csv"
    icm_distribucio_dst = semana_dir / "pulso_icm_distribucio.csv"
    marges_dst = semana_dir / "marges_branca.csv"
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

    productivitat_info = copy_csv_optional(productivitat_src, productivitat_dst, "Productivitat")
    if productivitat_info:
        productivitat_info.update(productivitat_meta(productivitat_dst))
        print(f"  productivitat.csv    · {productivitat_info['filas']:>6} filas · "
              f"últim any {productivitat_info['ultimo_any']}")

    ocupacio_info = copy_csv_optional(ocupacio_src, ocupacio_dst, "Ocupacio")
    if ocupacio_info:
        ocupacio_info.update(ocupacio_meta(ocupacio_dst))
        print(f"  ocupacio_comerc.csv  · {ocupacio_info['filas']:>6} filas · "
              f"últim any {ocupacio_info['ultimo_any']}")

    ipc_info = copy_csv_optional(ipc_src, ipc_dst, "IPC")
    if ipc_info:
        ipc_info.update(ipc_meta(ipc_dst))
        print(f"  ipc.csv              · {ipc_info['filas']:>6} filas · "
              f"últim periode {ipc_info['ultimo_periode']}")

    icm_info = capture_icm(icm_src, icm_dst)
    if icm_info:
        va = icm_info.get("general_real_var_anual")
        print(f"  pulso_icm.csv        · {icm_info['filas']:>6} filas · "
              f"últim periode {icm_info['ultimo_periodo']} · "
              f"general real var. anual {va:+.1f}%" if va is not None else
              f"  pulso_icm.csv        · {icm_info['filas']:>6} filas · "
              f"últim periode {icm_info['ultimo_periodo']}")

    icm_dist_info = capture_icm_distribucio(icm_distribucio_src, icm_distribucio_dst)
    if icm_dist_info:
        modes_str = " · ".join(
            f"{m}: {v:+.1f}%" for m, v in icm_dist_info["modes_real_var_anual"].items()
        )
        print(f"  pulso_icm_distribucio· {icm_dist_info['filas']:>6} filas · "
              f"últim periode {icm_dist_info['ultimo_periodo']} · {modes_str}")

    marges_info = copy_csv_optional(marges_src, marges_dst, "Marges branca")
    if marges_info:
        marges_info.update(marges_meta(marges_dst))
        estat = "verificat" if marges_info["verificat"] else "SENSE verificar"
        print(f"  marges_branca.csv    · {marges_info['filas']:>6} filas · "
              f"{marges_info['n_branques']} branques · últim any {marges_info['ultimo_any']} · "
              f"{estat}")

    prensa_info = capture_press(prensa_dst, obs_path, SETTINGS["prensa"]["dias_ventana"])
    print(
        f"  recopilacion_prensa  · {prensa_info['items']:>6} items · "
        f"{prensa_info['feeds_ok']} feeds con entradas"
    )
    if prensa_info.get("feeds_fallidos"):
        print(f"     feeds sin entradas: {', '.join(prensa_info['feeds_fallidos'])}")

    noticies_editor_info, noticies_editor_avisos = capture_noticies_editor(
        NOTICIES_EDITOR_PATH, semana_str, prensa_dst)
    if noticies_editor_info:
        print(f"  noticies_editor      · {len(noticies_editor_info)} notícia(es) [EDITOR] "
              f"afegides al recull")
    elif noticies_editor_avisos:
        print("  noticies_editor      · totes les URLs de l'editor han fallat el fetch "
              "(vegeu avisos), cap afegida al recull")
    else:
        print("  noticies_editor      · cap entrada per a aquesta setmana "
              "(fitxer absent o sense secció per a aquesta setmana)")
    for avis in noticies_editor_avisos:
        print(f"     {avis}")

    meta = {
        "semana_iso": lunes.strftime("%G-W%V"),
        "fecha_envio_prevista": semana_str,
        "captura": datetime.now(timezone.utc).isoformat(),
        "pulso_diario": cdmge_info,
        "pulso_europeo": europa_info,
        "productivitat": productivitat_info,
        "ocupacio": ocupacio_info,
        "ipc": ipc_info,
        "icm": icm_info,
        "icm_distribucio": icm_dist_info,
        "marges": marges_info,
        "prensa": prensa_info,
        "noticies_editor": noticies_editor_info,
        "noticies_editor_avisos": noticies_editor_avisos,
    }
    (semana_dir / "_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Snapshot completado en {semana_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
