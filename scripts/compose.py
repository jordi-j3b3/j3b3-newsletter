"""
Compone el HTML del email a partir del borrador Markdown.

Aplica transformaciones específicas a los bloques estructurados:
- Bloque 1 (cifra): los campos **Cifra:**, **Contexto:**, **Fuente:** se
  renderizan como una caja-exhibit visual.
- Bloque 3 (datos): la lista **Datos:** + países/valores se renderiza
  como barras horizontales divergentes.
- El campo **Titular:** alimenta el h1 de la cabecera del email.

Lee:
- output/semana-YYYY-MM-DD/newsletter.md
- templates/email_base.html

Escribe:
- output/semana-YYYY-MM-DD/newsletter.html

Uso:
    python scripts/compose.py --semana 2026-05-19 --numero 1
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import markdown as md_lib
import yaml
from dotenv import load_dotenv
from premailer import transform


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)


MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

MARKER_EXHIBIT = "MARKER_EXHIBIT_X7Y2"
MARKER_BARS = "MARKER_BARS_Z9K1"

FIRMA_FOOTER = (
    '<p style="margin:0 0 6px; font-family:\'DM Sans\',-apple-system,sans-serif; '
    'font-size:12px; color:#7f8c8d; line-height:1.5;">'
    'Jordi Bacaria. J3B3 Consulting.'
    '</p>\n            '
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", required=True)
    p.add_argument("--numero", type=int, required=True)
    return p.parse_args()


def strip_trazabilidad(text: str) -> str:
    """Elimina la sección TRAZABILIDAD (no se envía al email final)."""
    idx = text.find("### TRAZABILIDAD")
    return text[:idx].rstrip() + "\n" if idx >= 0 else text


def strip_markdown_artifacts(text: str) -> str:
    """Elimina artefactos que el modelo copia de las ediciones modelo del
    few-shot pero que el template HTML ya renderiza o que no deben aparecer
    en el cuerpo del email:

    1. Cabecera duplicada **EL PULSO DE LA SEMANA** + *Núm. X | Semana del...*
    2. Firma *— J3B3* tras la predicción (la marca está en el footer)
    3. Bloque de footer **Observatorio del Comercio** ... al final del cuerpo
    """
    # 1. Cabecera duplicada al principio del cuerpo
    text = re.sub(
        r"(?:^|\n)\s*(?:---\s*\n)?\s*"
        r"\*\*EL PULSO DE LA SEMANA\*\*\s*\n"
        r"\*[^*\n]*Núm\.[^*\n]*\*\s*\n"
        r"(?:\s*---\s*\n)?",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    # 2. Firma J3B3 sola en línea (con o sin asteriscos, em-dash/en-dash/guion)
    text = re.sub(
        r"\n\s*\*?\s*[—–\-]+\s*J3B3\s*\*?\s*(?=\n|\Z)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # 3. Bloque de footer al final del cuerpo (hasta fin del texto)
    text = re.sub(
        r"\n\s*(?:---\s*\n)?\s*\*\*Observatorio del Comercio\*\*.*\Z",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return text.rstrip() + "\n"


def extraer_meta(text: str) -> dict:
    """Extrae los campos de cabecera y el cuerpo del borrador.

    Devuelve: {subject, preheader, titular, body}
    body empieza después del último campo de cabecera encontrado.
    """
    subject_m = re.search(r"\*\*Asunto:\*\*\s*(.+)", text)
    preheader_m = re.search(r"\*\*Pre-header:\*\*\s*(.+)", text)
    titular_m = re.search(r"\*\*Titular:\*\*\s*(.+)", text)
    if not subject_m or not preheader_m:
        raise ValueError(
            "El borrador no contiene 'Asunto:' o 'Pre-header:' en el formato esperado. "
            "Revisar la generación."
        )
    body_start = max(m.end() for m in [subject_m, preheader_m, titular_m] if m)
    after = text[body_start:]
    # Consumir solo un separador '---' que esté al inicio del cuerpo (entre la
    # cabecera y el primer bloque). Buscar con find("---") era frágil: si el
    # borrador no trae ese separador post-cabecera, saltaba hasta el '---' del
    # footer y descartaba todo el cuerpo editorial.
    lead_sep = re.match(r"\s*\n?-{3,}[ \t]*\n", after)
    body = after[lead_sep.end():] if lead_sep else after
    return {
        "subject": subject_m.group(1).strip(),
        "preheader": preheader_m.group(1).strip(),
        "titular": titular_m.group(1).strip() if titular_m else "",
        "body": body.strip(),
    }


def semana_compacta(semana_str: str) -> str:
    """Devuelve el rango Mon-Sun de la semana que contiene la fecha.

    Ej.: '2026-05-19' (martes) → '18-24 mayo 2026'.
    """
    d = datetime.strptime(semana_str, "%Y-%m-%d")
    lunes = d - timedelta(days=d.weekday())
    domingo = lunes + timedelta(days=6)
    if lunes.month == domingo.month:
        return f"{lunes.day}-{domingo.day} {MESES_ES[domingo.month - 1]} {domingo.year}"
    return (f"{lunes.day} {MESES_ES[lunes.month - 1]} - "
            f"{domingo.day} {MESES_ES[domingo.month - 1]} {domingo.year}")


# --- Bloque 1: caja-exhibit ---------------------------------------------------

CIFRA_PATTERN = re.compile(
    r"\*\*◆\s*LA CIFRA DE LA SEMANA\s*\*\*\s*\n+"
    r"\*\*Cifra:\*\*\s*(.+?)\s*\n"
    r"\*\*Contexto:\*\*\s*(.+?)\s*\n"
    r"\*\*Fuente:\*\*\s*(.+?)\s*\n",
    re.IGNORECASE,
)


def extraer_cifra(body: str) -> tuple[str, dict | None]:
    m = CIFRA_PATTERN.search(body)
    if not m:
        return body, None
    data = {
        "cifra": m.group(1).strip(),
        "contexto": m.group(2).strip(),
        "fuente": m.group(3).strip(),
    }
    new_body = body[:m.start()] + f"\n\n{MARKER_EXHIBIT}\n\n" + body[m.end():]
    return new_body, data


def render_exhibit(data: dict) -> str:
    cifra = data["cifra"]
    m = re.match(r"^(.*?)\s*(%|pp|p\.p\.)\s*$", cifra)
    if m:
        cifra_html = f'{m.group(1).strip()}<span class="exhibit-unit">{m.group(2)}</span>'
    else:
        cifra_html = cifra
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="exhibit-table">'
        '<tr><td class="exhibit-box">'
        f'<div class="exhibit-cifra">{cifra_html}</div>'
        f'<div class="exhibit-context">{data["contexto"]}</div>'
        f'<div class="exhibit-source">{data["fuente"]}</div>'
        '</td></tr></table>'
    )


# --- Bloque 3: barras horizontales --------------------------------------------

# Subtítulo aceptado en dos formatos: '**Datos:** <texto>' (ediciones antiguas)
# o '**<texto>**' (subtítulo en negrita sin prefijo). Sin esta tolerancia, un
# borrador que omita 'Datos:' caía a lista plana en vez de barras divergentes.
DATOS_PATTERN = re.compile(
    r"\*\*◆\s*DATOS DE LA SEMANA\s*\*\*\s*\n+"
    r"\*\*(?:Datos:\*\*\s*)?(.+?)(?:\*\*)?\s*\n\n"
    r"((?:-\s+[^\n]+\n?)+)",
    re.IGNORECASE,
)


def extraer_datos(body: str) -> tuple[str, dict | None]:
    m = DATOS_PATTERN.search(body)
    if not m:
        return body, None
    subtitle = m.group(1).strip()
    list_text = m.group(2)
    items = []
    for line in list_text.strip().split("\n"):
        ml = re.match(r"-\s+(.+?):\s*(.+)", line.strip())
        if ml:
            items.append((ml.group(1).strip(), ml.group(2).strip()))
    if not items:
        return body, None
    new_body = body[:m.start()] + f"\n\n{MARKER_BARS}\n\n" + body[m.end():]
    return new_body, {"subtitle": subtitle, "items": items}


def parse_value(s: str) -> float | None:
    """Parsea valores como '+4,1%', '-2.0pp', '−1,99 %'. Devuelve None si falla."""
    s = (s.replace("−", "-").replace("–", "-")
           .replace(",", ".").replace("%", "")
           .replace("pp", "").replace("p.p.", "")
           .replace("+", "").strip())
    try:
        return float(s)
    except ValueError:
        return None


def render_bars(data: dict) -> str:
    subtitle = data["subtitle"]
    items = data["items"]
    parsed = []
    for label, value_str in items:
        v = parse_value(value_str)
        if v is None:
            continue
        parsed.append((label, v, value_str))
    if not parsed:
        return ""

    max_abs = max(abs(v) for _, v, _ in parsed) or 1.0
    half_width_px = 140
    max_bar_px = int(half_width_px * 0.9)

    rows = []
    for label, v, original in parsed:
        bar_width = max(2, int(abs(v) / max_abs * max_bar_px))
        if v < 0:
            bar_cls = "bar bar-neg"
            value_cls = "bar-value bar-value-neg"
        elif v >= 4:
            bar_cls = "bar bar-pos-strong"
            value_cls = "bar-value bar-value-pos-strong"
        else:
            bar_cls = "bar bar-pos-light"
            value_cls = "bar-value bar-value-pos"

        if v < 0:
            bar_cell = (
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0" class="bar-track">'
                '<tr>'
                f'<td align="right" class="bar-side bar-side-left">'
                f'<div class="{bar_cls}" style="width:{bar_width}px;">&nbsp;</div>'
                '</td>'
                '<td class="bar-side bar-side-right">&nbsp;</td>'
                '</tr></table>'
            )
        else:
            bar_cell = (
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0" class="bar-track">'
                '<tr>'
                '<td class="bar-side bar-side-left">&nbsp;</td>'
                f'<td align="left" class="bar-side bar-side-right">'
                f'<div class="{bar_cls}" style="width:{bar_width}px;">&nbsp;</div>'
                '</td>'
                '</tr></table>'
            )
        rows.append(
            '<tr>'
            f'<td class="bar-label" align="right">{label}</td>'
            f'<td class="bar-cell">{bar_cell}</td>'
            f'<td class="{value_cls}">{original}</td>'
            '</tr>'
        )

    return (
        f'<h2 class="data-title">Datos de la semana · {subtitle}</h2>'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="bars-table">'
        + "".join(rows) +
        '</table>'
        '<p class="bars-legend">↑ variación interanual</p>'
    )


# --- Render principal --------------------------------------------------------

def render(semana_str: str, numero: int) -> tuple[str, str, str, str]:
    md_path = ROOT / "output" / f"semana-{semana_str}" / "newsletter.md"
    template_path = ROOT / "templates" / "email_base.html"

    md_text = strip_trazabilidad(md_path.read_text(encoding="utf-8"))
    meta = extraer_meta(md_text)

    body = strip_markdown_artifacts(meta["body"])
    body, cifra_data = extraer_cifra(body)
    body, datos_data = extraer_datos(body)

    body_html = md_lib.markdown(body, extensions=["extra", "tables", "sane_lists"])

    # Sustituir marcadores limpiando posibles <p> wrappers
    if cifra_data:
        exhibit_html = render_exhibit(cifra_data)
        body_html = re.sub(rf"<p>\s*{MARKER_EXHIBIT}\s*</p>", exhibit_html, body_html)
        body_html = body_html.replace(MARKER_EXHIBIT, exhibit_html)
    if datos_data:
        bars_html = render_bars(datos_data)
        body_html = re.sub(rf"<p>\s*{MARKER_BARS}\s*</p>", bars_html, body_html)
        body_html = body_html.replace(MARKER_BARS, bars_html)

    # Bloques restantes con marca ◆ (NUESTRA LECTURA, LA PREDICCIÓN) → h2.
    # Restringim el capture a majúscules+espais: si el model posa el text
    # de la predicció dins el **...** (ex: **◆ LA PREDICCIÓN: Si la presió...
    # **) el regex no fa match i el cos queda com a <p>, no com a <h2>.
    body_html = re.sub(
        r"<p>\s*<strong>◆\s*([A-ZÁÉÍÓÚÜÑ\s·]+?)\s*</strong>\s*</p>",
        r"<h2>\1</h2>",
        body_html,
    )

    template = template_path.read_text(encoding="utf-8")
    titular = meta["titular"] or meta["subject"]
    rendered = (
        template
        .replace("{{subject}}", meta["subject"])
        .replace("{{preheader}}", meta["preheader"])
        .replace("{{titular}}", titular)
        .replace("{{numero}}", str(numero))
        .replace("{{semana_str}}", semana_compacta(semana_str))
        .replace("{{body_html}}", body_html)
        .replace("{{url_publica}}", SETTINGS["newsletter"]["url_publica"])
    )

    _url = SETTINGS["newsletter"]["url_publica"]
    rendered = rendered.replace(
        f'<p style="margin:6px 0 0;"><a href="{_url}">Web</a>',
        FIRMA_FOOTER + f'<p style="margin:6px 0 0;"><a href="{_url}">Web</a>',
    )

    rendered = transform(
        rendered,
        disable_validation=True,
        cssutils_logging_level="CRITICAL",
        keep_style_tags=True,
    )
    return rendered, meta["subject"], meta["preheader"], titular


def main() -> int:
    args = parse_args()
    html, subject, preheader, titular = render(args.semana, args.numero)
    out_path = ROOT / "output" / f"semana-{args.semana}" / "newsletter.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"HTML compuesto en {out_path}")
    print(f"  Asunto:    {subject}")
    print(f"  Preheader: {preheader}")
    print(f"  Titular:   {titular}")
    print(f"  Tamaño:    {len(html)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
