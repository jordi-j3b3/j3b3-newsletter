"""
Programa la newsletter setmanal a Brevo amb enviament automatic dilluns 08:30.

Pensat per a GitHub Actions: corre cada diumenge a la nit i deixa la campanya
programada a Brevo perque s'enviï l'endema al mati. Flux complet:

1. Detecta la setmana (proper dilluns) i el numero d'edicio (max(historial)+1).
2. Executa snapshot -> generate -> compose (els tres scripts existents).
3. Crea una campanya programada a Brevo (POST /v3/emailCampaigns amb scheduledAt).
4. Desa el brevo_campaign_id al historial_editorial.json.
5. Envia un correu transaccional de notificacio a jordi@j3b3.com amb instruccions
   per cancel·lar si cal.

Us:
    python scripts/schedule.py                          # detecta tot
    python scripts/schedule.py --semana 2026-06-08 --numero 4
    python scripts/schedule.py --dry-run                # simulacio sense Brevo
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Paraules clau macro: BCE, política monetària, PIB, inflació, Banco de España.
# Inclou variants de moviments de tipus ("alza/subida/bajada/recorte de tipos")
# que apareixen als titulars mediàtics sense escriure "tipos de interés" explícitament.
_MACRO_RE = re.compile(
    r"BCE|Banco Central Europeo|banque centrale|ECB\b|"
    r"tipos? de inter[eé]s|tipus d[''']inter[eè]s|pol[ií]tica monetari[ao]|"
    r"alza de tipos|subida de tipos|bajada de tipos|recorte de tipos|"
    r"pujada de tipus|baixada de tipus|retallada de tipus|"
    r"endurecimiento monetario|flexibilizaci[oó]n monetaria|"
    r"PIB|producto interior bruto|producte interior brut|"
    r"inflaci[oó]n?|inflaci[oó]|IPC|preus? de consum|precios? al consumo|"
    r"Banco de Espa[nñ]a|Banc d[''']Espanya|"
    r"\bFed\b|Reserva Federal|"
    r"eur[ií]bor|Euribor|"
    r"deuda p[uú]blica|deute p[uú]blic|"
    r"recesi[oó]n?|recessió|"
    r"creixement econ[oò]mic|crecimiento econ[oó]mico",
    re.IGNORECASE,
)

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brevo import _session  # noqa: E402
from compose import extraer_meta, strip_trazabilidad  # noqa: E402
from mirror import mirror_to_dashboard  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"
NOTIFICATION_TO = "jordi@j3b3.com"


def proxim_dilluns(avui: date | None = None) -> str:
    """Pròxim dilluns >= demà. Si avui és dilluns, retorna el dilluns vinent."""
    avui = avui or date.today()
    delta = (7 - avui.weekday()) % 7
    if delta == 0:
        delta = 7
    return (avui + timedelta(days=delta)).strftime("%Y-%m-%d")


def carrega_historial() -> list:
    if not HISTORIAL_PATH.exists():
        return []
    try:
        data = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def desa_historial(entries: list) -> None:
    HISTORIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORIAL_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def detecta_numero(historial: list) -> int:
    nums = [e.get("numero") for e in historial if isinstance(e.get("numero"), int)]
    return (max(nums) + 1) if nums else 1


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


def executa_pipeline(semana: str, numero: int, context_extra: str = "") -> None:
    py = sys.executable
    # Heretem explícitament tot l'entorn perquè els subprocessos vegin les
    # API keys passades des del workflow (en alguns contextos d'Actions, no
    # propagar env de manera explícita pot fer que generate.py no rebi
    # ANTHROPIC_API_KEY i caigui amb "Could not resolve authentication method").
    child_env = os.environ.copy()
    print(
        f"[pipeline] env keys presents: "
        f"ANTHROPIC_API_KEY={'OK' if child_env.get('ANTHROPIC_API_KEY') else 'MISSING'}, "
        f"BREVO_API_KEY={'OK' if child_env.get('BREVO_API_KEY') else 'MISSING'}, "
        f"OBSERVATORI_PATH={child_env.get('OBSERVATORI_PATH', 'MISSING')}"
    )

    def run(cmd: list[str]) -> None:
        print(f"\n$ {' '.join(cmd)}")
        r = subprocess.run(cmd, cwd=ROOT, env=child_env)
        if r.returncode != 0:
            raise SystemExit(f"Pas fallit: {' '.join(cmd)}")

    # 1. Snapshot — congela dades + recopilacion_prensa.md (font de la detecció macro).
    run([py, "scripts/snapshot.py", "--semana", semana])

    # 2. Detecció de fets macro a la premsa del snapshot i injecció com a context
    #    addicional al prompt de generate.py. Així Sonnet els pondera per al Bloque 1
    #    i la predicció abans de generar, en lloc de detectar-los només a posteriori
    #    (que era el comportament antic: la detecció alimentava només la notificació).
    noticias_macro = detectar_noticias_macro(semana)
    contexts = []
    if noticias_macro:
        contexts.append(construir_contexto_macro(noticias_macro))
        print(f"[pipeline] {len(noticias_macro)} fet(s) macro detectat(s) a la premsa "
              f"→ injectats a generate.py via --context-extra")
    else:
        print("[pipeline] Cap fet macro detectat a la premsa; generate.py sense context macro.")
    if context_extra:
        contexts.append(context_extra)
        print("[pipeline] Context macro manual (--context-extra) afegit al pipeline.")

    generate_cmd = [py, "scripts/generate.py", "--semana", semana, "--numero", str(numero)]
    if contexts:
        generate_cmd += ["--context-extra", "\n\n".join(contexts)]

    # 3. Generate → 4. Compose → 5. Publica web.
    run(generate_cmd)
    run([py, "scripts/compose.py", "--semana", semana, "--numero", str(numero)])
    run([py, "scripts/publish_web.py", "--semana", semana, "--numero", str(numero)])


def crea_campanya_programada(
    *,
    name: str,
    subject: str,
    preheader: str,
    html: str,
    from_name: str,
    from_email: str,
    list_id: str,
    scheduled_at_iso: str,
) -> str:
    s = _session()
    payload = {
        "name": name,
        "subject": subject,
        "htmlContent": html,
        "sender": {"name": from_name, "email": from_email},
        "recipients": {"listIds": [int(list_id)]},
        "header": preheader,
        "scheduledAt": scheduled_at_iso,
    }
    r = s.post("https://api.brevo.com/v3/emailCampaigns", json=payload, timeout=30)
    if not r.ok:
        print(f"Error Brevo (crear campanya): HTTP {r.status_code}", file=sys.stderr)
        print(f"Respuesta: {r.text[:500]}", file=sys.stderr)
        r.raise_for_status()
    cid = r.json().get("id")
    if not cid:
        raise RuntimeError(f"Resposta inesperada de Brevo: {r.text[:300]}")
    return str(cid)


def envia_notificacio(
    *,
    to: str,
    subject: str,
    html: str,
    from_email: str,
    from_name: str,
) -> None:
    s = _session()
    payload = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html,
    }
    r = s.post("https://api.brevo.com/v3/smtp/email", json=payload, timeout=30)
    if not r.ok:
        print(f"Error Brevo (notificacio): HTTP {r.status_code} {r.text[:300]}", file=sys.stderr)


def extreu_metadades(semana: str) -> dict:
    """Llegeix titular, subject, preheader, predicció del .md generat."""
    md_path = ROOT / "output" / f"semana-{semana}" / "newsletter.md"
    html_path = ROOT / "output" / f"semana-{semana}" / "newsletter.html"
    if not md_path.exists():
        raise FileNotFoundError(f"No existeix {md_path}")
    md_text = md_path.read_text(encoding="utf-8")
    meta = extraer_meta(strip_trazabilidad(md_text))
    titular = ""
    m = re.search(r"^\*\*Titular:\*\*\s*(.+)$", md_text, re.MULTILINE)
    if m:
        titular = m.group(1).strip()
    prediccion = ""
    p = re.search(
        r"\*\*◆\s*LA PREDICCI[ÓO]N\*\*\s*\n+(.+?)(?=\n+\*—|\n+\*\*◆|\n+---|\Z)",
        md_text, re.DOTALL,
    )
    if p:
        prediccion = p.group(1).strip()
    return {
        "subject": meta.get("subject", ""),
        "preheader": meta.get("preheader", ""),
        "titular": titular,
        "prediccion": prediccion,
        "html": html_path.read_text(encoding="utf-8") if html_path.exists() else "",
    }


def detectar_noticias_macro(semana: str) -> list[dict]:
    """Cerca notícies amb paraules clau macro a la recopilació de premsa del snapshot."""
    prensa_path = ROOT / "data" / f"semana-{semana}" / "recopilacion_prensa.md"
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


def suspen_campanya(campaign_id: str) -> bool:
    """Desprograma una campanya a Brevo (PUT status=suspended; HTTP 204).
    Retorna True si s'ha suspès. No fatal: si falla, avisa i segueix."""
    s = _session()
    r = s.put(
        f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/status",
        json={"status": "suspended"}, timeout=30,
    )
    if not r.ok:
        print(f"Avís: no s'ha pogut suspendre la campanya {campaign_id}: "
              f"HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    return True


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--semana", help="Default: proper dilluns")
    p.add_argument("--numero", type=int, help="Default: max(historial)+1")
    p.add_argument("--dry-run", action="store_true",
                   help="No executa pipeline ni crida Brevo; mostra payload simulat")
    p.add_argument("--skip-pipeline", action="store_true",
                   help="Suposa que snapshot/generate/compose ja estan fets")
    p.add_argument("--force", action="store_true",
                   help="Crea la campanya encara que la setmana ja en tingui una d'activa")
    p.add_argument("--replace", action="store_true",
                   help="Regenera: suspèn la campanya ja programada d'aquesta setmana, "
                        "la treu de l'historial i en crea una de nova amb el mateix número")
    p.add_argument("--context-extra", default="",
                   help="Context macro addicional, afegit al que es detecta "
                        "automàticament a la premsa i passat a generate.py")
    args = p.parse_args()

    historial = carrega_historial()
    semana = args.semana or proxim_dilluns()

    # --replace: substitueix la campanya d'aquesta setmana. Suspèn la campanya
    # activa a Brevo i treu l'entrada de l'historial; així la regeneració crea
    # contingut nou amb el mateix número (i el sistema anti-repetició veu les
    # edicions anteriors, ja enriquides).
    if args.replace:
        restants = []
        for e in historial:
            if (e.get("semana") == semana and e.get("brevo_campaign_id")
                    and not e.get("cancelled_at_utc")):
                cid = e["brevo_campaign_id"]
                print(f"[replace] Suspenent campanya existent núm. {e.get('numero')} "
                      f"(campaign {cid})…")
                suspen_campanya(cid)
            else:
                restants.append(e)
        if len(restants) != len(historial):
            historial = restants
            desa_historial(historial)
            print("[replace] Entrada(es) anterior(s) suspesa(es) i tretes de l'historial.")

    numero = args.numero or detecta_numero(historial)

    print(f"Setmana objectiu (dilluns d'enviament): {semana}")
    print(f"Numero d'edicio: {numero}")

    # Idempotència: no crear una segona campanya si la setmana ja en té una d'activa.
    # Protegeix contra execucions duplicades (cron tardà + disparada manual, reintents…),
    # que abans inflaven el número i programaven dos enviaments per a la mateixa setmana.
    actives = [e for e in historial
               if e.get("semana") == semana
               and e.get("brevo_campaign_id")
               and not e.get("cancelled_at_utc")]
    if actives:
        ult = actives[-1]
        msg = (f"Ja hi ha una campanya activa per a la setmana {semana}: "
               f"núm. {ult.get('numero')}, campaign {ult.get('brevo_campaign_id')}.")
        if args.force:
            print(f"\n[--force] {msg} Es crea igualment.")
        elif args.dry_run:
            print(f"\n[DRY-RUN] {msg} En execució real NO es crearia res (--force per forçar).")
        else:
            print(f"\n{msg}\nNo es crea res (idempotent). Usa --force per forçar.")
            return 0

    # Pipeline
    if args.dry_run:
        print("\n[DRY-RUN] No s'executa snapshot/generate/compose")
        meta = {
            "subject": "(dry-run) <s'extrauria del .md>",
            "preheader": "(dry-run) <s'extrauria del .md>",
            "titular": "(dry-run) <s'extrauria del .md>",
            "prediccion": "(dry-run) <s'extrauria del .md>",
            "html": "",
        }
        md_path = ROOT / "output" / f"semana-{semana}" / "newsletter.md"
        if md_path.exists():
            print(f"[DRY-RUN] .md ja existeix a {md_path.relative_to(ROOT)}, l'extrec")
            meta = extreu_metadades(semana)
    elif args.skip_pipeline:
        print("\n[--skip-pipeline] Suposo snapshot/generate/compose ja fets.")
        meta = extreu_metadades(semana)
    else:
        executa_pipeline(semana, numero, context_extra=args.context_extra)
        meta = extreu_metadades(semana)

    # Configuracio Brevo
    from_email = os.environ.get("BREVO_FROM_EMAIL")
    from_name = os.environ.get("BREVO_FROM_NAME", "Observatorio del Comercio")
    list_id = os.environ.get("BREVO_LIST_PILOT_ID")
    if not from_email or not list_id:
        print("Error: falten BREVO_FROM_EMAIL o BREVO_LIST_PILOT_ID a l'entorn", file=sys.stderr)
        return 2

    scheduled_at_iso = f"{semana}T08:30:00+02:00"
    name = f"Núm. {numero} · semana {semana}"

    print("\n" + "=" * 64)
    print("  CAMPANYA A PROGRAMAR (Brevo)")
    print("=" * 64)
    print(f"  Nom:         {name}")
    print(f"  Assumpte:    {meta['subject']}")
    print(f"  Preheader:   {meta['preheader']}")
    print(f"  Remitent:    {from_name} <{from_email}>")
    print(f"  Lista ID:    {list_id}")
    print(f"  Programat:   {scheduled_at_iso}")
    print(f"  HTML chars:  {len(meta['html'])}")
    print()

    if args.dry_run:
        payload_preview = {
            "endpoint": "POST https://api.brevo.com/v3/emailCampaigns",
            "name": name,
            "subject": meta["subject"],
            "header_preheader": meta["preheader"],
            "sender": {"name": from_name, "email": from_email},
            "recipients": {"listIds": [list_id]},
            "scheduledAt": scheduled_at_iso,
            "htmlContent_length_chars": len(meta["html"]),
        }
        print("[DRY-RUN] Payload Brevo /emailCampaigns:")
        print(json.dumps(payload_preview, indent=2, ensure_ascii=False))
        print()
        print(f"[DRY-RUN] Notificacio a {NOTIFICATION_TO}:")
        print(f"  Assumpte: [OBSERVATORI] Núm. {numero} programat per dilluns 8:30")
        print(f"  Titular:  {meta['titular']}")
        print(f"  Prediccio: {meta['prediccion'][:150]}{'…' if len(meta['prediccion']) > 150 else ''}")
        print()
        print("[DRY-RUN] No s'ha tocat Brevo ni el historial. Fi.")
        return 0

    # Crida real a Brevo
    campaign_id = crea_campanya_programada(
        name=name,
        subject=meta["subject"],
        preheader=meta["preheader"],
        html=meta["html"],
        from_name=from_name,
        from_email=from_email,
        list_id=list_id,
        scheduled_at_iso=scheduled_at_iso,
    )
    print(f"Campaign ID: {campaign_id}")

    # Desa al historial SENSE trepitjar l'entrada enriquida que generate.py acaba
    # d'escriure (cifra/angulo_bloc1/tema_prediccion/noticias), que és el que fa
    # servir el sistema anti-repetició la setmana següent. Recarreguem (generate.py
    # ha escrit després que carreguéssim historial al principi) i fusionem els camps
    # de Brevo dins l'entrada d'aquesta edició. Si no n'hi ha (p.ex. error d'extracció
    # a generate.py), n'afegim una de nova com a fallback.
    brevo_fields = {
        "brevo_campaign_id": campaign_id,
        "scheduled_at": scheduled_at_iso,
        "asunto": meta["subject"],
        "titular": meta["titular"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    historial = carrega_historial()
    entrada = next((e for e in historial
                    if e.get("numero") == numero and e.get("semana") == semana), None)
    if entrada is not None:
        entrada.update(brevo_fields)
    else:
        historial.append({"numero": numero, "semana": semana, **brevo_fields})
    desa_historial(historial)
    print(f"Historial actualitzat: {HISTORIAL_PATH.relative_to(ROOT)}")

    # Fets macro detectats automàticament al snapshot. Quan n'hi ha, ja s'han
    # injectat al prompt de generate.py via --context-extra (vegeu executa_pipeline),
    # de manera que Sonnet els ha ponderat per al Bloque 1 i la predicció. La
    # notificació només els llista per a transparència i auditoria.
    noticias_macro = detectar_noticias_macro(semana)
    if noticias_macro:
        macro_items = "".join(
            f"<li><strong>{n['data']}</strong> — {n['titol']}"
            f"<br><span style='color:#666;font-size:0.9em'>{n['font']}</span></li>"
            for n in noticias_macro
        )
        macro_html = (
            f"<h3 style='font-family:sans-serif'>Fets macro detectats i injectats "
            f"({len(noticias_macro)})</h3>"
            f"<p style='color:#666;font-size:0.9em'>Injectats automàticament al prompt "
            f"de generació; Sonnet els ha ponderat per a la cifra del Bloque 1 i la "
            f"predicció.</p>"
            f"<ul style='font-family:sans-serif'>{macro_items}</ul>"
        )
    else:
        macro_html = (
            "<h3 style='font-family:sans-serif'>Fets macro detectats</h3>"
            "<p style='color:#666'>Cap notícia macro detectada automàticament "
            "(BCE, PIB, inflació, Banco de España, euríbor). Cap context macro "
            "injectat a la generació.</p>"
        )

    # Notificacio
    notification_html = (
        f"<h2 style='font-family:sans-serif'>Newsletter programada</h2>"
        f"<p><strong>Núm. {numero}</strong> · setmana {semana}</p>"
        f"<p><strong>Programat per:</strong> dilluns {semana} a les 08:30 (CEST)</p>"
        f"<p><strong>Assumpte:</strong> {meta['subject']}</p>"
        f"<p><strong>Titular:</strong> {meta['titular']}</p>"
        f"<p><strong>Predicció:</strong> {meta['prediccion']}</p>"
        f"<hr>"
        f"{macro_html}"
        f"<p style='font-family:sans-serif;font-size:0.9em;color:#444'>"
        f"Si vols afegir context macro no detectat, cancel·la i regenera "
        f"<strong>abans de les 8:00 del dilluns</strong>:<br>"
        f"1. <code>python scripts/cancel.py --semana {semana}</code><br>"
        f"2. <code>python scripts/generate.py --semana {semana} --numero {numero} "
        f"--force --context-extra \"[context macro]\"</code><br>"
        f"3. Recomposa i reprograma: "
        f"<code>python scripts/schedule.py --semana {semana} --replace --skip-pipeline</code>"
        f"</p>"
        f"<hr>"
        f"<p>Per cancel·lar l'enviament sense regenerar:</p>"
        f"<pre style='background:#f4f4f4;padding:12px'>"
        f"python scripts/cancel.py --semana {semana}"
        f"</pre>"
        f"<p style='color:#888;font-size:0.85em'>Campaign ID: {campaign_id}</p>"
    )
    envia_notificacio(
        to=NOTIFICATION_TO,
        subject=f"[OBSERVATORI] Núm. {numero} programat per dilluns 8:30",
        html=notification_html,
        from_email=from_email,
        from_name=from_name,
    )
    print(f"Notificació enviada a {NOTIFICATION_TO}")

    # Mirall automàtic al dashboard (L_Lecturas + tesi vigent). Com que
    # l'enviament real el fa Brevo al programat, send.py no s'executa mai en el
    # flux automàtic; per això publiquem aquí, amb la setmana i el número ja
    # resolts. Condicionat a MIRROR_ON_SCHEDULE=1 (només CI) perquè una
    # execució local de schedule.py no pugi res al repo viu per sorpresa.
    # No fatal: la campanya ja està programada; un error de mirall es resol a mà.
    if os.environ.get("MIRROR_ON_SCHEDULE") == "1":
        print("\n[mirror] Publicant l'edició al dashboard...")
        try:
            mirror_to_dashboard(semana, numero)
        except Exception as e:  # noqa: BLE001
            print(f"[mirror] Error no fatal en el mirall: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
