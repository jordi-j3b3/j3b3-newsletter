"""
Sincronitza els TRES punts de sortida d'una edició des d'una única font.

El problema que resol
---------------------
Una edició acaba en tres llocs independents, cadascun amb la seva comanda:
la campanya de Brevo, el mirall del dashboard (`observatori-comerc/data/
newsletter/`) i la web estàtica (`docs/pulso/`). Cap dels tres es torna a
disparar quan el contingut es corregeix després de la generació inicial, i el
resultat ha estat el MATEIX incident quatre vegades:

  Núm. 10 (2026-07-06)  mirall no regenerat després de refer l'edició
  Núm. 12 (2026-07-20)  mirall i web amb el contingut de la campanya cancel·lada
  Núm. 14 (2026-08-02)  correcció al Bloc 1 després que el cron ja hagués
                        publicat als tres llocs amb la versió incompleta
  Núm. 16 (2026-08-16)  edició regenerada de dalt a baix; van caldre tres
                        comandes manuals seguides i una comprovació a mà

Cada cop es va descobrir per casualitat, i tres vegades hi va haver contingut
d'una campanya cancel·lada viu a la web durant dies.

Aquest script fa el cicle sencer i, sobretot, **comprova al final que els tres
llocs diuen el mateix**. La comprovació és la meitat del valor: sense ella
tornaríem a confiar que la comanda ha fet efecte.

Font única
----------
`output/semana-X/newsletter.md`. Si no hi és —cas habitual: l'ha generat la CI,
on `output/` és efímer— es recupera del mirall del dashboard, que és el
procediment ja documentat al ROADMAP. Es diu d'on surt, sempre.

Què fa i què no fa
------------------
- Recompon l'HTML des del markdown (compose.py) perquè els tres llocs derivin
  del mateix text.
- Brevo: si la campanya de la setmana està en `queued`/`draft`/`suspended`,
  actualitza htmlContent + subject + header i **rellegeix** per confirmar (la
  gotcha de l'editor web que reverteix el contingut). Si ja està `sent`, NO la
  toca: un correu enviat no es pot canviar, i ho diu clar.
- Mirall del dashboard: `mirror_to_dashboard()` (commit + push a
  observatori-comerc).
- Web estàtica: `publish_web.py` (num-N.html + índex + sitemap).
- Comprovació final del titular als quatre llocs (md, Brevo, mirall, web).

Ús
--
    python scripts/resync.py --semana 2026-08-17
    python scripts/resync.py --semana 2026-08-17 --dry-run
    python scripts/resync.py --semana 2026-08-17 --nomes web,mirall

Codis de sortida
----------------
  0  els tres llocs (o els sincronitzats) coincideixen
  1  error d'ús / no s'ha trobat la font
  2  hi ha discrepàncies després de sincronitzar
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent))

HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"
DESTINS = ("brevo", "mirall", "web")


# ------------------------------------------------------------------ utilitats

def _titular(md: str) -> str:
    m = re.search(r"(?m)^\*\*Titular:\*\*\s*(.+)$", md)
    return m.group(1).strip() if m else ""


def _obs_root() -> Path:
    return Path(os.environ.get("OBSERVATORI_REPO_PATH")
                or os.environ.get("OBSERVATORI_PATH")
                or (ROOT.parent / "observatori-comerc")).expanduser().resolve()


def entrada_activa(semana: str) -> dict | None:
    """L'entrada de l'historial d'aquesta setmana que NO està cancel·lada.

    Es filtra per `cancelled_at_utc` perquè el fitxer conserva els registres de
    les campanyes suspeses (criteri del projecte: no s'esborra mai un registre),
    i sincronitzar contra una campanya cancel·lada és precisament l'incident que
    volem tancar.
    """
    if not HISTORIAL_PATH.exists():
        return None
    historial = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
    actives = [e for e in historial
               if e.get("semana") == semana and e.get("brevo_campaign_id")
               and not e.get("cancelled_at_utc")]
    return actives[-1] if actives else None


def localitza_font(semana: str) -> tuple[Path, str]:
    """Retorna (ruta, procedencia) del markdown que farà de font única."""
    local = ROOT / "output" / f"semana-{semana}" / "newsletter.md"
    if local.is_file():
        return local, "output/ local"
    mirall = _obs_root() / "data" / "newsletter" / f"semana-{semana}.md"
    if mirall.is_file():
        return mirall, f"mirall del dashboard ({mirall})"
    raise FileNotFoundError(
        f"No s'ha trobat el markdown de la setmana {semana} ni a "
        f"{local} ni al mirall {mirall}. Sense font no es sincronitza res."
    )


# ------------------------------------------------------------------- destins

def sincronitza_brevo(semana: str, numero: int, html: str, subject: str,
                      preheader: str, dry: bool,
                      titular: str = "") -> tuple[str, str]:
    """Retorna (estat, titular_a_brevo). No toca una campanya ja enviada."""
    from brevo import get_campaign, update_campaign

    entrada = entrada_activa(semana)
    if not entrada:
        return ("sense campanya activa a l'historial per a aquesta setmana", "")
    cid = str(entrada["brevo_campaign_id"])

    camp = get_campaign(cid, with_html=True)
    estat = camp.get("status", "?")
    if estat == "sent":
        return (f"campanya {cid} JA ENVIADA ({camp.get('sentDate')}): no es "
                f"toca. El correu que ha rebut la gent no es pot canviar; "
                f"mirall i web sí que s'alineen amb el markdown",
                _titular_html(camp.get("htmlContent") or "", titular))
    if dry:
        return (f"[dry-run] campanya {cid} ({estat}): s'actualitzaria "
                f"htmlContent + subject + header",
                _titular_html(camp.get("htmlContent") or "", titular))

    update_campaign(cid, htmlContent=html, subject=subject, header=preheader)
    # Rellegida NOVA, no reaprofitada: si algú ha obert la campanya a l'editor
    # web de Brevo, l'htmlContent revertiria i el PUT semblaria correcte.
    confirm = get_campaign(cid, with_html=True)
    tit = _titular_html(confirm.get("htmlContent") or "", titular)
    return (f"campanya {cid} ({estat}) actualitzada i reverificada", tit)


def _titular_html(html: str, titular_esperat: str = "") -> str:
    """Titular trobat dins l'HTML de la campanya.

    NO es pot llegir del `<title>`: a la plantilla de correu el `<title>` porta
    l'ASSUMPTE, no el titular editorial, i comparar-lo contra el titular donava
    sempre discrepància. Es busca el titular esperat dins el cos, que és on viu
    de debò; si no hi és, es torna el `<title>` com a pista per al diagnòstic.
    """
    if titular_esperat:
        nucli = titular_esperat.rstrip(".").strip()
        # El renderitzat pot partir línies o inserir etiquetes entre paraules:
        # es compara sobre el text pla amb espais normalitzats.
        pla = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
        if nucli and nucli in pla:
            return titular_esperat
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def sincronitza_mirall(semana: str, numero: int, dry: bool) -> tuple[str, str]:
    from mirror import mirror_to_dashboard

    desti = _obs_root() / "data" / "newsletter" / f"semana-{semana}.md"
    if dry:
        return (f"[dry-run] es copiaria a {desti} i es reescriuria "
                f"tesi_vigent.json", _titular(desti.read_text(encoding='utf-8'))
                if desti.is_file() else "")
    mirror_to_dashboard(semana, numero)
    return ("mirall publicat (commit + push a observatori-comerc)",
            _titular(desti.read_text(encoding="utf-8")) if desti.is_file() else "")


def sincronitza_web(semana: str, numero: int, dry: bool) -> tuple[str, str]:
    pagina = ROOT / "docs" / "pulso" / f"num-{numero}.html"
    if dry:
        return (f"[dry-run] es regeneraria {pagina} + índex + sitemap",
                _titular_manifest(numero))
    r = subprocess.run(
        [sys.executable, "scripts/publish_web.py", "--semana", semana,
         "--numero", str(numero)], cwd=ROOT)
    if r.returncode != 0:
        return ("ERROR: publish_web.py ha fallat", "")
    return (f"web regenerada ({pagina.name} + índex + sitemap)",
            _titular_manifest(numero))


def _titular_manifest(numero: int) -> str:
    man = ROOT / "docs" / "pulso" / "manifest.json"
    if not man.is_file():
        return ""
    dades = json.loads(man.read_text(encoding="utf-8"))
    entrades = dades["entries"] if isinstance(dades, dict) else dades
    for e in entrades:
        if e.get("numero") == numero:
            return str(e.get("titular", "")).strip()
    return ""


# ----------------------------------------------------------------------- main

def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", required=True, help="YYYY-MM-DD del dilluns")
    p.add_argument("--numero", type=int,
                   help="Número d'edició (default: el de l'historial)")
    p.add_argument("--dry-run", action="store_true",
                   help="Mostra què faria, sense tocar res")
    p.add_argument("--nomes", default=",".join(DESTINS),
                   help=f"Destins a sincronitzar, separats per coma. "
                        f"Opcions: {','.join(DESTINS)}")
    p.add_argument("--sense-compose", action="store_true",
                   help="No recomponguis l'HTML; usa el newsletter.html existent")
    args = p.parse_args()

    destins = [d.strip() for d in args.nomes.split(",") if d.strip()]
    desconeguts = set(destins) - set(DESTINS)
    if desconeguts:
        print(f"Error: destí desconegut {desconeguts}. Opcions: {DESTINS}",
              file=sys.stderr)
        return 1

    try:
        font, procedencia = localitza_font(args.semana)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    entrada = entrada_activa(args.semana)
    numero = args.numero or (entrada or {}).get("numero")
    if not numero:
        print("Error: no s'ha pogut determinar el número d'edició; passa "
              "--numero", file=sys.stderr)
        return 1

    md = font.read_text(encoding="utf-8")
    titular_font = _titular(md)

    print(f"resync · Núm. {numero} · setmana {args.semana}")
    print(f"  font: {procedencia}")
    print(f"  titular de referència: «{titular_font}»")
    if args.dry_run:
        print("  MODE DRY-RUN: no es toca res")

    # Si la font és el mirall, cal copiar-la a output/ perquè compose.py i
    # publish_web.py (que llegeixen output/) treballin sobre el mateix text.
    local = ROOT / "output" / f"semana-{args.semana}" / "newsletter.md"
    if font != local and not args.dry_run:
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(md, encoding="utf-8")
        print(f"  markdown recuperat a {local.relative_to(ROOT)}")

    # Recomposició de l'HTML des del markdown.
    html_path = ROOT / "output" / f"semana-{args.semana}" / "newsletter.html"
    subject = preheader = ""
    if args.sense_compose:
        if not html_path.is_file():
            print(f"Error: --sense-compose però no hi ha {html_path}",
                  file=sys.stderr)
            return 1
        from compose import extraer_meta, strip_trazabilidad
        meta = extraer_meta(strip_trazabilidad(md))
        subject, preheader = meta["subject"], meta["preheader"]
        html = html_path.read_text(encoding="utf-8")
        print("  HTML: es reutilitza el newsletter.html existent")
    elif args.dry_run:
        from compose import extraer_meta, strip_trazabilidad
        meta = extraer_meta(strip_trazabilidad(md))
        subject, preheader = meta["subject"], meta["preheader"]
        html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        print("  HTML: [dry-run] es recompondria des del markdown")
    else:
        from compose import render
        html, subject, preheader, _ = render(args.semana, numero)
        html_path.write_text(html, encoding="utf-8")
        print(f"  HTML recompost des del markdown ({len(html)} chars)")

    # --- destins ---------------------------------------------------------
    resultats: dict[str, tuple[str, str]] = {}
    if "brevo" in destins:
        try:
            resultats["brevo"] = sincronitza_brevo(
                args.semana, numero, html, subject, preheader, args.dry_run,
                titular_font)
        except Exception as e:
            resultats["brevo"] = (f"ERROR: {e}", "")
    if "mirall" in destins:
        try:
            resultats["mirall"] = sincronitza_mirall(args.semana, numero, args.dry_run)
        except Exception as e:
            resultats["mirall"] = (f"ERROR: {e}", "")
    if "web" in destins:
        try:
            resultats["web"] = sincronitza_web(args.semana, numero, args.dry_run)
        except Exception as e:
            resultats["web"] = (f"ERROR: {e}", "")

    print("\nAccions:")
    for d in DESTINS:
        if d in resultats:
            print(f"  {d:<7} {resultats[d][0]}")

    # --- comprovació final ----------------------------------------------
    # Aquesta part és la meitat del valor de l'script: no donar per fet que la
    # comanda ha fet efecte. Els incidents del Núm.10/12/14 es van descobrir per
    # casualitat setmanes després precisament perquè ningú comparava.
    print("\nComprovació del titular a cada lloc:")
    problemes = []
    print(f"  {'markdown':<10} «{titular_font}»")
    for d in DESTINS:
        if d not in resultats:
            print(f"  {d:<10} (no sincronitzat en aquesta execució)")
            continue
        estat, titular_desti = resultats[d]
        if estat.startswith("ERROR"):
            problemes.append(f"{d}: {estat}")
            print(f"  {d:<10} ERROR")
            continue
        if not titular_desti:
            print(f"  {d:<10} (no s'ha pogut llegir el titular per comparar)")
            continue
        coincideix = titular_font and titular_font.rstrip(".") in titular_desti
        marca = "OK " if coincideix else "NO "
        print(f"  {d:<10} {marca}«{titular_desti[:80]}»")
        if not coincideix and not args.dry_run:
            problemes.append(
                f"{d}: el titular no coincideix amb el markdown "
                f"(«{titular_desti[:60]}»)")

    if problemes:
        print("\nDISCREPÀNCIES:", file=sys.stderr)
        for pr in problemes:
            print(f"  ✗ {pr}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("\n[dry-run] res tocat.")
    else:
        print("\nEls llocs sincronitzats diuen el mateix.")
        if "brevo" in resultats and "JA ENVIADA" in resultats["brevo"][0]:
            print("Recorda: la campanya ja estava enviada; el correu rebut "
                  "conserva la versió antiga.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
