"""
Detecció de fets macroeconòmics a la recopilació de premsa del snapshot.

Mòdul compartit entre:
  - generate.py: injecta el context macro al prompt de Sonnet (perquè el
    ponderi a la cifra del Bloque 1 i a la predicció del Bloque 4).
  - schedule.py: llista els fets macro a la notificació d'auditoria.

Centralitzar-ho aquí garanteix que la detecció NO divergeixi entre el
pipeline automàtic (schedule.py → generate.py com a subprocés) i una
execució manual de generate.py: en tots dos casos Sonnet veu els mateixos
fets macro de la setmana.
"""
from __future__ import annotations

import re
from pathlib import Path

# Paraules clau macro: BCE, política monetària, PIB, inflació, Banco de España.
# Inclou variants de moviments de tipus ("alza/subida/bajada/recorte de tipos")
# que apareixen als titulars mediàtics sense escriure "tipos de interés" explícitament.
_MACRO_RE = re.compile(
    r"BCE|Banco Central Europeo|banque centrale|ECB\b|"
    r"tipos? de inter[eé]s|tipus d['’´]inter[eè]s|pol[ií]tica monetari[ao]|"
    r"alza de tipos|subida de tipos|bajada de tipos|recorte de tipos|"
    r"pujada de tipus|baixada de tipus|retallada de tipus|"
    r"endurecimiento monetario|flexibilizaci[oó]n monetaria|"
    r"PIB|producto interior bruto|producte interior brut|"
    r"inflaci[oó]n?|inflaci[oó]|IPC|preus? de consum|precios? al consumo|"
    r"Banco de Espa[nñ]a|Banc d['’´]Espanya|"
    r"\bFed\b|Reserva Federal|"
    r"eur[ií]bor|Euribor|"
    r"deuda p[uú]blica|deute p[uú]blic|"
    r"recesi[oó]n?|recessió|"
    r"creixement econ[oò]mic|crecimiento econ[oó]mico",
    re.IGNORECASE,
)


def detectar_noticias_macro(prensa_path: Path | str) -> list[dict]:
    """Cerca notícies amb paraules clau macro a la recopilació de premsa.

    Args:
        prensa_path: ruta al recopilacion_prensa.md del snapshot.
    Returns:
        Llista de dicts {data, titol, font}; buida si el fitxer no existeix
        o no hi ha cap coincidència.
    """
    prensa_path = Path(prensa_path)
    if not prensa_path.exists():
        return []
    results = []
    current_date = ""
    current_title = ""
    current_source = ""
    current_text = ""

    for line in prensa_path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^## \d{4}-\d{2}-\d{2}", line):
            current_date = line[3:].strip()
        elif line.startswith("### "):
            if current_title and _MACRO_RE.search(current_text):
                results.append({"data": current_date, "titol": current_title, "font": current_source})
            current_title = line[4:].strip()
            current_source = ""
            current_text = current_title
        elif line.startswith("- Fuente: "):
            current_source = line[10:].strip()
            current_text += " " + current_source
        elif line.startswith("- Snippet: "):
            current_text += " " + line[11:].strip()

    if current_title and _MACRO_RE.search(current_text):
        results.append({"data": current_date, "titol": current_title, "font": current_source})

    return results


def construir_contexto_macro(noticias_macro: list[dict]) -> str:
    """Formata els fets macro detectats com a bloc de context per a generate.py.

    El text s'injecta dins <CONTEXT_MACRO> al prompt de Sonnet (just abans de
    <RECOPILACION_PRENSA>). Aquestes notícies JA figuren a la recopilació de
    premsa; el bloc de context les ressalta perquè el model les ponderi
    especialment a la cifra del Bloque 1 i, sobretot, a la predicció del Bloque 4.
    """
    items = "\n".join(
        f"- {n['data']} — {n['titol']}" + (f" ({n['font']})" if n.get("font") else "")
        for n in noticias_macro
    )
    return (
        "CONTEXTO MACROECONÓMICO DE LA SEMANA (detectado automáticamente en la "
        "prensa del snapshot). Estas noticias ya figuran en <RECOPILACION_PRENSA>; "
        "se destacan aquí porque marcan el entorno monetario y de consumo de la "
        "semana:\n\n"
        f"{items}\n\n"
        "Tenlos en cuenta especialmente para: (a) la lectura de la cifra del "
        "Bloque 1, si el contexto monetario o de inflación la condiciona; y "
        "(b) la predicción del Bloque 4, que debe ser coherente con este entorno "
        "macro (tipos, inflación, ciclo). NO los conviertas en una de las tres "
        "noticias del Bloque 2 solo por aparecer aquí: el Bloque 2 sigue sus "
        "propias reglas de selección (diversidad de medio y noticia de proximidad)."
    )
