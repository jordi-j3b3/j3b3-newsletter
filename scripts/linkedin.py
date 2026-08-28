"""
Esborrany de post de LinkedIn a partir d'una edició ja validada d'El Pulso.

Què fa
------
Llegeix el markdown d'una edició (la mateixa font única que fa servir
`resync.py`: `output/semana-X/newsletter.md` i, si no hi és, el mirall del
dashboard), hi afegeix la guia de veu de `config/estil_personal_jordi.md` i la
llista de tics a evitar de `config/estil_editorial.md`, i demana a l'API
d'Anthropic un esborrany de post. El resultat va a
`output/linkedin_draft_{numero}.md`, llest per revisar i copiar.

El post NO és un resum de l'edició: és la tesi reescrita amb la veu de Jordi,
en català i en primera persona, mentre que el butlletí és en castellà i en
registre d'informe. Per això les dues guies entren amb papers diferents —
l'estil personal com a model a seguir, l'editorial NOMÉS com a inventari de
tics a evitar, perquè el registre del butlletí no contamini el post.

Independència
-------------
Aquest script **no forma part del pipeline del butlletí**. No el crida
`schedule.py`, no s'encadena a `verify.py` ni a l'enviament per Brevo, i no
escriu res al `config/historial_editorial.json`. Si falla, no bloqueja cap
enviament: només deixa de generar un esborrany. Execució sempre manual.

Ús
--
    python scripts/linkedin.py --numero 18
    python scripts/linkedin.py                  # última edició disponible
    python scripts/linkedin.py --semana 2026-08-31

Codis de sortida
----------------
  0  esborrany escrit
  1  no s'ha pogut generar (edició no trobada, guia absent, error d'API)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent))

# La localització del markdown d'una edició viu en un sol lloc del repo
# (`resync.py`): duplicar-la aquí seria el camí curt cap a dues idees diferents
# d'on és la font, que és l'arrel dels incidents de miralls desincronitzats.
from resync import localitza_font  # noqa: E402

HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"
ESTIL_PERSONAL_PATH = ROOT / "config" / "estil_personal_jordi.md"
ESTIL_EDITORIAL_PATH = ROOT / "config" / "estil_editorial.md"

with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)

SYSTEM_BASE = """Ets un assistent d'escriptura que genera esborranys de posts \
de LinkedIn per a Jordi Bacaria, economista expert en comerç minorista.

Segueix estrictament config/estil_personal_jordi.md pel que fa a veu,
estructura i anti-patrons. Usa config/estil_editorial.md únicament
per saber quins tics evitar (no per adoptar-ne el registre).

El post ha de:
- Reescriure la tesi de l'edició amb paraules pròpies de Jordi,
  NO resumir el newsletter
- Integrar l'Observatori del Comerç Minorista com a font de manera
  epistemològica, no publicitària
- Acabar amb una invitació suau a subscriure's a El Pulso de la Setmana
  (indicar que l'URL va als comentaris, no al cos del post)
- Llengua: català
- Longitud: 180-250 paraules sense el CTA"""

# Restriccions de sortida que no són de veu sinó de format del lliurable: el
# fitxer s'ha de poder copiar tal qual a LinkedIn.
SYSTEM_EXTRA = """
Restriccions de sortida:
- Retorna NOMÉS el text del post, sense preàmbul, sense cometes que
  l'embolcallin i sense comentaris teus.
- Sense emojis, en cap posició.
- Sense capçaleres de markdown ni negretes decoratives: LinkedIn no les
  renderitza i delaten el text generat.
- No copiïs frases literals del butlletí. Les xifres sí que han de ser
  exactament les de l'edició; no n'inventis cap ni n'arrodoneixis cap.
- La longitud és un límit, no una orientació: el cos ha de quedar entre 180
  i 250 paraules sense comptar el CTA. Compta-les i retalla si et passes;
  el que sobra sempre és context, no l'anàlisi."""


def carrega_historial() -> list:
    if not HISTORIAL_PATH.exists():
        return []
    try:
        return json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Avís: historial il·legible ({e}); es continua sense.", file=sys.stderr)
        return []


def _actives(historial: list) -> list:
    """Entrades que corresponen a edicions realment enviades o programades.

    El fitxer conserva els registres de les campanyes cancel·lades (criteri del
    projecte: no s'esborra mai un registre) i alguna entrada de diagnòstic
    d'edicions que no van arribar a sortir. Cap de les dues ha de ser l'origen
    d'un post públic.
    """
    return [e for e in historial
            if e.get("brevo_campaign_id") and not e.get("cancelled_at_utc")
            and not e.get("estat") and not e.get("estado")]


def resol_edicio(numero: int | None, semana: str | None) -> tuple[int, str]:
    """Decideix quina edició es fa servir i retorna (numero, semana)."""
    historial = _actives(carrega_historial())

    if semana:
        candidates = [e for e in historial if e.get("semana") == semana]
        num = numero or (candidates[-1].get("numero") if candidates else None)
        if num is None:
            raise LookupError(f"No hi ha cap edició activa per a la setmana {semana}.")
        return int(num), semana

    if numero is not None:
        candidates = [e for e in historial if e.get("numero") == numero]
        if not candidates:
            raise LookupError(
                f"No hi ha cap edició activa amb el número {numero} a l'historial. "
                f"Passa --semana si la vols generar igualment.")
        return numero, str(candidates[-1]["semana"])

    if not historial:
        raise LookupError("L'historial no té cap edició activa.")
    ultima = sorted(historial, key=lambda e: (str(e.get("semana")), e.get("numero", 0)))[-1]
    return int(ultima["numero"]), str(ultima["semana"])


def cos_edicio(md: str) -> str:
    """El text de l'edició sense la secció de traçabilitat.

    La traçabilitat és material intern d'auditoria (números de regla, rutes de
    CSV, avisos de mètode). No ha d'entrar mai al context d'un text públic.
    """
    return re.split(r"###\s*TRAZABILIDAD", md)[0].strip()


def construeix_prompts(cos: str, numero: int, semana: str) -> tuple[str, str]:
    if not ESTIL_PERSONAL_PATH.exists():
        raise FileNotFoundError(
            f"Falta {ESTIL_PERSONAL_PATH.relative_to(ROOT)}, que és la guia de veu: "
            f"sense ella el post no és de Jordi i no té sentit generar-lo.")
    estil_personal = ESTIL_PERSONAL_PATH.read_text(encoding="utf-8").strip()

    if ESTIL_EDITORIAL_PATH.exists():
        estil_editorial = ESTIL_EDITORIAL_PATH.read_text(encoding="utf-8").strip()
    else:
        estil_editorial = ""
        print(f"Avís: no hi ha {ESTIL_EDITORIAL_PATH.name}; es genera sense la "
              f"llista de tics a evitar.", file=sys.stderr)

    system = SYSTEM_BASE + "\n" + SYSTEM_EXTRA + "\n\n" + (
        f"<ESTIL_PERSONAL_JORDI>\n{estil_personal}\n</ESTIL_PERSONAL_JORDI>\n\n")
    if estil_editorial:
        system += (
            "<TICS_A_EVITAR font=estil_editorial.md>\n"
            "Aquest document és la guia del BUTLLETÍ, no del post. Serveix "
            "NOMÉS per saber quins tics d'escriptura s'han d'evitar. No n'has "
            "d'adoptar el registre, ni la llengua, ni l'estructura de blocs.\n\n"
            f"{estil_editorial}\n</TICS_A_EVITAR>")

    user = (
        f"Aquesta és l'edició Núm. {numero} d'El Pulso de la Setmana "
        f"(enviament {semana}). Escriu-ne el post de LinkedIn.\n\n"
        f"<EDICIO>\n{cos}\n</EDICIO>")
    return system, user


def genera(system: str, user: str, model: str, temperatura: float) -> str:
    from anthropic import Anthropic
    client = Anthropic()
    r = client.messages.create(
        model=model,
        max_tokens=1500,
        temperature=temperatura,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    # Per si el model embolcalla la resposta en un bloc de codi.
    text = re.sub(r"^```(?:markdown|text)?\s*\n?", "", text)
    return re.sub(r"\n?```\s*$", "", text).strip()


def _paraules(text: str) -> int:
    return len(re.findall(r"[\w·’'-]+", text))


def revisa(post: str) -> list[str]:
    """Comprovacions lleugeres sobre l'esborrany. Avisen, mai bloquegen: això
    és un esborrany per revisar a mà, no una peça que s'enviï sola."""
    avisos = []
    # L'objectiu de longitud és "sense el CTA", i el CTA és sempre l'últim
    # paràgraf: comptar-lo tot inflaria la xifra i l'avís no serviria de res.
    cos = post.rsplit("\n\n", 1)[0] if "\n\n" in post else post
    paraules = _paraules(cos)
    if not 180 <= paraules <= 250:
        avisos.append(f"longitud fora de l'objectiu: {paraules} paraules sense "
                      f"el CTA (objectiu 180-250)")
    # Negació binària, l'anti-patró número u de les dues guies. Té dues formes
    # habituals: "no A, sinó B" i "no és A: és B" (amb punt, coma o dos punts).
    for patro, nom in (
        (r"\bno\b[^.;!?]{0,90}\bsinó\b", "no… sinó"),
        (r"\bno és\b[^.:;!?]{0,80}[.:;]\s*(?:é|É)s\b", "no és A: és B"),
    ):
        for m in re.finditer(patro, post, re.I):
            avisos.append(f"negació binària («{nom}»): «{m.group(0)[:70]}…»")
    if re.search(r"(?m)^#{1,6}\s", post):
        avisos.append("hi ha capçaleres de markdown; l'estil en demana cap")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", post):
        avisos.append("hi ha emojis: treu-los")
    if re.search(r"https?://", post):
        avisos.append("hi ha una URL al cos; segons l'estil va als comentaris")
    for tic in ("sinergi", "ecosistema", "palanca", "full de ruta", "fulla de ruta"):
        if tic in post.lower():
            avisos.append(f"paraula de la llista d'anti-patrons: «{tic}»")
    return avisos


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--numero", type=int, help="Número d'edició (default: l'última)")
    p.add_argument("--semana", help="Dilluns de l'edició (YYYY-MM-DD), si cal forçar-la")
    p.add_argument("--model", default=os.environ.get("LINKEDIN_MODEL"),
                   help="Model d'Anthropic (default: el de settings.yaml)")
    p.add_argument("--stdout", action="store_true",
                   help="Escriu el post també per pantalla")
    args = p.parse_args()

    try:
        numero, semana = resol_edicio(args.numero, args.semana)
        font, procedencia = localitza_font(semana)
    except (LookupError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"linkedin.py · Núm. {numero} · setmana {semana}")
    print(f"  font: {procedencia}")

    cos = cos_edicio(font.read_text(encoding="utf-8"))
    if not cos:
        print("Error: l'edició no té cos després de treure la traçabilitat.",
              file=sys.stderr)
        return 1

    try:
        system, user = construeix_prompts(cos, numero, semana)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    model = args.model or SETTINGS["modelo"]["modelo"]
    print(f"  generant amb {model}...")
    try:
        post = genera(system, user, model, float(SETTINGS["modelo"]["temperatura"]))
    except Exception as e:                                    # noqa: BLE001
        print(f"Error de generació ({e}). No s'ha escrit res.", file=sys.stderr)
        return 1

    if not post:
        print("Error: el model no ha retornat text.", file=sys.stderr)
        return 1

    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    desti = out_dir / f"linkedin_draft_{numero}.md"
    segell = datetime.now().strftime("%Y-%m-%d %H:%M")
    desti.write_text(f"{post}\n\n<!-- Generat: {segell} | Edició: {numero} -->\n",
                     encoding="utf-8")

    for avis in revisa(post):
        print(f"  avís: {avis}", file=sys.stderr)

    print(f"  esborrany a {desti.relative_to(ROOT)}")
    if args.stdout:
        print("\n" + "-" * 60 + f"\n{post}\n" + "-" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
