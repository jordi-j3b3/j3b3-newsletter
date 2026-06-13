"""
Publica El Pulso de la semana com a HTML web estàtic per a indexació a Google News.

Genera tres fitxers al directori web/:
  web/pulso/num-{N}.html  — la nota de l'edició amb metadades Google News
  web/pulso/index.html    — índex de totes les edicions
  web/sitemap.xml         — sitemap amb extensió Google News (<news:news>)

Llegeix:
  output/semana-YYYY-MM-DD/newsletter.md   (generat per compose.py)
  templates/web_base.html
  web/pulso/manifest.json                  (creat/actualitzat per aquest script)

Ús:
  python scripts/publish_web.py --semana 2026-06-08 --numero 6
  python scripts/publish_web.py --backfill
  python scripts/publish_web.py --backfill --output-dir /path/to/output
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import markdown as md_lib

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "scripts"))
from compose import (  # noqa: E402
    MARKER_BARS,
    MARKER_EXHIBIT,
    MESES_ES,
    extraer_cifra,
    extraer_datos,
    extraer_meta,
    render_bars,
    render_exhibit,
    semana_compacta,
    strip_markdown_artifacts,
    strip_trazabilidad,
)

WEB_DIR = ROOT / "docs"
WEB_PULSO_DIR = WEB_DIR / "pulso"
MANIFEST_PATH = WEB_PULSO_DIR / "manifest.json"
BASE_URL = "https://pulso.j3b3.com"
INDEX_URL = f"{BASE_URL}/pulso/"

HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"


# --- Helpers -----------------------------------------------------------------

def semana_a_fecha_larga(semana_str: str) -> str:
    """'2026-06-08' → '8 de junio de 2026'"""
    d = datetime.strptime(semana_str, "%Y-%m-%d")
    return f"{d.day} de {MESES_ES[d.month - 1]} de {d.year}"


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_manifest(entries: list[dict]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries_sorted = sorted(entries, key=lambda e: e.get("numero", 0))
    MANIFEST_PATH.write_text(
        json.dumps(entries_sorted, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_manifest(numero: int, semana: str, titular: str, subject: str,
                    description: str, published_iso: str) -> None:
    entries = load_manifest()
    entry = {
        "numero": numero,
        "semana": semana,
        "titular": titular,
        "subject": subject,
        "description": description,
        "published_iso": published_iso,
        "url": f"{BASE_URL}/pulso/num-{numero}.html",
    }
    # Reemplaça entrada existent pel mateix numero o afegeix
    updated = [e for e in entries if e.get("numero") != numero]
    updated.append(entry)
    save_manifest(updated)


# --- Render web HTML ---------------------------------------------------------

def render_web(semana: str, numero: int, output_root: Path | None = None) -> str:
    """
    Llegeix newsletter.md, renderitza HTML web (sense premailer) i escriu
    web/pulso/num-{N}.html. Retorna l'HTML generat.
    """
    output_root = output_root or ROOT / "output"
    md_path = output_root / f"semana-{semana}" / "newsletter.md"
    template_path = ROOT / "templates" / "web_base.html"

    if not md_path.exists():
        raise FileNotFoundError(f"No existeix {md_path}")

    md_text = strip_trazabilidad(md_path.read_text(encoding="utf-8"))
    meta = extraer_meta(md_text)

    body = strip_markdown_artifacts(meta["body"])
    body, cifra_data = extraer_cifra(body)
    body, datos_data = extraer_datos(body)

    body_html = md_lib.markdown(body, extensions=["extra", "tables", "sane_lists"])

    if cifra_data:
        exhibit_html = render_exhibit(cifra_data)
        body_html = re.sub(rf"<p>\s*{MARKER_EXHIBIT}\s*</p>", exhibit_html, body_html)
        body_html = body_html.replace(MARKER_EXHIBIT, exhibit_html)
    if datos_data:
        bars_html = render_bars(datos_data)
        body_html = re.sub(rf"<p>\s*{MARKER_BARS}\s*</p>", bars_html, body_html)
        body_html = body_html.replace(MARKER_BARS, bars_html)

    body_html = re.sub(
        r"<p>\s*<strong>◆\s*([^<]+?)\s*</strong>\s*</p>",
        r"<h2>\1</h2>",
        body_html,
    )

    titular = meta["titular"] or meta["subject"]
    published_iso = f"{semana}T08:30:00+02:00"
    canonical_url = f"{BASE_URL}/pulso/num-{numero}.html"

    template = template_path.read_text(encoding="utf-8")
    rendered = (
        template
        .replace("{{subject}}", meta["subject"])
        .replace("{{description}}", meta["preheader"])
        .replace("{{titular}}", titular)
        .replace("{{numero}}", str(numero))
        .replace("{{semana_str}}", semana_compacta(semana))
        .replace("{{body_html}}", body_html)
        .replace("{{canonical_url}}", canonical_url)
        .replace("{{published_iso}}", published_iso)
        .replace("{{index_url}}", INDEX_URL)
        .replace("{{fecha_publicacion}}", semana_a_fecha_larga(semana))
    )

    WEB_PULSO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEB_PULSO_DIR / f"num-{numero}.html"
    out_path.write_text(rendered, encoding="utf-8")
    print(f"  Web HTML: {out_path.relative_to(ROOT)}")

    update_manifest(numero, semana, titular, meta["subject"], meta["preheader"], published_iso)
    return rendered


# --- Index -------------------------------------------------------------------

def generate_index() -> None:
    """Genera web/pulso/index.html amb la llista de totes les edicions."""
    entries = load_manifest()
    if not entries:
        print("  Index: cap entrada al manifest, saltant.")
        return

    entries_desc = sorted(entries, key=lambda e: e.get("numero", 0), reverse=True)

    items_html = ""
    for e in entries_desc:
        d = datetime.fromisoformat(e["published_iso"])
        fecha_larga = f"{d.day} de {MESES_ES[d.month - 1]} de {d.year}"
        items_html += (
            f'<li class="edition-item">'
            f'<span class="edition-num">Núm. {e["numero"]}</span>'
            f'<span class="edition-date">{fecha_larga}</span>'
            f'<a class="edition-link" href="{e["url"]}">{e["titular"]}</a>'
            f'<p class="edition-desc">{e["description"]}</p>'
            f'</li>\n'
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>El Pulso de la semana — Todas las ediciones · Observatorio del Comercio</title>
  <meta name="description" content="Archivo completo de El Pulso de la semana, la publicación semanal del Observatorio del Comercio sobre el sector retail español.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{INDEX_URL}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,600;1,400&family=DM+Serif+Display&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 0; background: #f4f4f2; font-family: 'DM Sans', -apple-system, sans-serif; color: #1a1a1a; -webkit-font-smoothing: antialiased; }}
    a {{ color: #0055a4; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page-wrapper {{ max-width: 720px; margin: 0 auto; padding: 0 16px 48px; }}
    .breadcrumb {{ font-size: 12px; color: #7f8c8d; padding: 16px 0 0; }}
    .breadcrumb a {{ color: #7f8c8d; }}
    header.page-header {{ background: #ffffff; margin-top: 16px; padding: 40px 48px 32px; border-bottom: 1px solid #e8f0fe; }}
    .eyebrow {{ color: #5a9fd4; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 500; margin: 0 0 12px; }}
    h1 {{ font-family: 'DM Serif Display', Georgia, serif; font-size: 28px; color: #0055a4; font-weight: 400; margin: 0 0 10px; }}
    .page-desc {{ font-size: 14px; color: #7f8c8d; font-style: italic; margin: 0; line-height: 1.6; }}
    ul.edition-list {{ list-style: none; margin: 0; padding: 0; }}
    li.edition-item {{ background: #ffffff; padding: 24px 48px; border-bottom: 1px solid #f0f0ee; }}
    li.edition-item:hover {{ background: #fafbfd; }}
    .edition-num {{ font-size: 11px; font-weight: 600; color: #5a9fd4; letter-spacing: 0.1em; text-transform: uppercase; display: block; margin-bottom: 4px; }}
    .edition-date {{ font-size: 12px; color: #aaa; display: block; margin-bottom: 6px; }}
    a.edition-link {{ font-family: 'DM Serif Display', Georgia, serif; font-size: 20px; color: #0055a4; display: block; margin-bottom: 6px; line-height: 1.3; }}
    p.edition-desc {{ font-size: 13px; color: #7f8c8d; font-style: italic; margin: 0; line-height: 1.5; }}
    .page-footer {{ background: #ffffff; padding: 24px 48px; font-size: 12px; color: #aaa; }}
    @media (max-width: 680px) {{
      header.page-header, li.edition-item, .page-footer {{ padding-left: 20px; padding-right: 20px; }}
      h1 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>
<div class="page-wrapper">
  <nav class="breadcrumb">
    <a href="https://pulso.j3b3.com">Inicio</a>
    <span>›</span>
    <span>El Pulso</span>
  </nav>
  <header class="page-header">
    <p class="eyebrow">Observatorio del Comercio · J3B3 Consulting</p>
    <h1>El Pulso de la semana</h1>
    <p class="page-desc">Análisis semanal del sector retail español. Una cifra, nuestra lectura, el mapa europeo y una predicción concreta.</p>
  </header>
  <ul class="edition-list">
{items_html}  </ul>
  <div class="page-footer">
    <a href="https://pulso.j3b3.com">Observatorio del Comercio</a> ·
    <a href="https://www.j3b3.com">J3B3 Consulting</a>
  </div>
</div>
</body>
</html>
"""
    out_path = WEB_PULSO_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  Index:    {out_path.relative_to(ROOT)} ({len(entries_desc)} edicions)")


# --- Sitemap -----------------------------------------------------------------

def generate_sitemap() -> None:
    """Genera web/sitemap.xml amb extensió Google News."""
    entries = load_manifest()

    url_blocks = []

    # Index de totes les edicions
    url_blocks.append(f"""  <url>
    <loc>{INDEX_URL}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>""")

    for e in sorted(entries, key=lambda x: x.get("numero", 0)):
        lastmod = e["published_iso"][:10]  # YYYY-MM-DD
        titular_escaped = (
            e["titular"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        url_blocks.append(f"""  <url>
    <loc>{e["url"]}</loc>
    <news:news>
      <news:publication>
        <news:name>Observatorio del Comercio</news:name>
        <news:language>es</news:language>
      </news:publication>
      <news:publication_date>{e["published_iso"]}</news:publication_date>
      <news:title>{titular_escaped}</news:title>
    </news:news>
    <lastmod>{lastmod}</lastmod>
    <changefreq>never</changefreq>
    <priority>0.8</priority>
  </url>""")

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
        + "\n".join(url_blocks)
        + "\n</urlset>\n"
    )

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEB_DIR / "sitemap.xml"
    out_path.write_text(sitemap_xml, encoding="utf-8")
    print(f"  Sitemap:  {out_path.relative_to(ROOT)} ({len(entries)} entrades + índex)")


# --- Backfill ----------------------------------------------------------------

def backfill(output_root: Path) -> None:
    """
    Genera HTML web per a totes les edicions disponibles a output_root.

    Llegeix config/historial_editorial.json per resoldre el numero de cada
    semana. Si una semana té múltiples entrades al historial (re-runs, cancel·lats),
    usa la última entrada que NO tingui cancelled_at_utc.
    """
    if not HISTORIAL_PATH.exists():
        print("Error: no existeix config/historial_editorial.json", file=sys.stderr)
        return

    historial: list[dict] = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))

    # Construeix mapa semana → numero: última entrada no cancel·lada per semana
    semana_to_numero: dict[str, int] = {}
    for entry in historial:
        semana = entry.get("semana")
        numero = entry.get("numero")
        if not semana or not isinstance(numero, int):
            continue
        if entry.get("cancelled_at_utc"):
            continue
        semana_to_numero[semana] = numero  # última entrada guanya

    # Busca tots els newsletter.md disponibles a output_root
    found = sorted(output_root.glob("semana-*/newsletter.md"))
    if not found:
        print(f"No s'han trobat newsletter.md a {output_root}")
        return

    print(f"Backfill: {len(found)} edicions trobades a {output_root}")
    ok = 0
    skipped = 0
    for md_path in found:
        semana = md_path.parent.name.replace("semana-", "")
        numero = semana_to_numero.get(semana)
        if numero is None:
            print(f"  Saltant semana {semana}: no trobada al historial o cancel·lada")
            skipped += 1
            continue
        try:
            render_web(semana, numero, output_root=output_root)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  Error semana {semana}: {exc}", file=sys.stderr)
            skipped += 1

    print(f"Backfill completat: {ok} OK, {skipped} saltades")

    generate_index()
    generate_sitemap()


# --- Main --------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--semana", help="Data de la setmana (YYYY-MM-DD)")
    p.add_argument("--numero", type=int, help="Número d'edició")
    p.add_argument("--backfill", action="store_true",
                   help="Genera HTML per a totes les edicions disponibles")
    p.add_argument("--output-dir", type=Path,
                   help="Directori output/ alternatiu (útil per a backfill des de OneDrive)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_dir or ROOT / "output"

    if args.backfill:
        backfill(output_root)
        return 0

    if not args.semana or args.numero is None:
        print("Error: --semana i --numero són obligatoris (o usa --backfill)", file=sys.stderr)
        return 1

    print(f"Publicant Núm. {args.numero} (semana {args.semana})...")
    render_web(args.semana, args.numero, output_root=output_root)
    generate_index()
    generate_sitemap()
    print("Publicació web completada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
