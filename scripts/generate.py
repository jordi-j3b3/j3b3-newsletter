"""
Genera el borrador en Markdown de la edición semanal con Sonnet 4.6.

Lee:
- templates/linea_editorial.md     (cacheable vía prompt cache)
- config/estil_editorial.md        (cacheable vía prompt cache; permanente, no se consume)
- templates/data_dictionary.md     (cacheable vía prompt cache)
- data/semana-YYYY-MM-DD/*         (snapshot semanal, ya congelado)

Escribe:
- output/semana-YYYY-MM-DD/newsletter.md      borrador editable
- output/semana-YYYY-MM-DD/dades_origen/*     copia auditable del snapshot

Modos editoriales:
  P1 — dada fresca mana: Eurostat, productivitat o ocupació han publicat
       periode nou. La cifra protagonista és la novetat; el Titular en deriva.
  P2 — tesi mana: cap dataset clau actualitzat. L'editor fixa el Titular
       (--titular) i l'AI tria la dada que millor l'argumenta.

Anti-repetició de la cifra protagonista:
  Si la cifra del Bloque 1 repeteix dataset+periode respecte l'edició
  anterior (mateix indicador, mateix mes), es reintenta la generació fins a
  MAX_REINTENTOS_CIFRA_REPETIDA vegades amb una instrucció explícita de triar
  un altre dataset o un altre periode del snapshot (veure es_dada_repetida).

Uso:
    python scripts/generate.py --semana 2026-05-19 --numero 1
    python scripts/generate.py --semana 2026-06-23 --numero 9 \\
        --titular "El coste laboral reordena el retail."
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from macro import detectar_noticias_macro, construir_contexto_macro  # noqa: E402


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)


HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"
HISTORIAL_VENTANA = 6  # ediciones recientes a inyectar en el prompt
MAX_REINTENTOS_CIFRA_REPETIDA = 1  # reintentos si la cifra del Bloque 1 repite dataset+periodo

TESI_SETMANA_PATH = ROOT / "config" / "tesi_setmana.md"


def load_tesi_setmana() -> str:
    """Llegeix la tesi setmanal fixada per l'editor, si existeix.

    Equivalent a --context-extra però llegit automàticament del fitxer, sense
    haver de passar el flag a mà. Retorna "" si el fitxer no existeix (el
    pipeline funciona igual que fins ara). No l'esborra ni el renombra aquí
    — això es fa a marcar_tesi_usada() després d'una generació exitosa."""
    if not TESI_SETMANA_PATH.exists():
        return ""
    return TESI_SETMANA_PATH.read_text(encoding="utf-8").strip()


def marcar_tesi_usada() -> None:
    """Renombra config/tesi_setmana.md a tesi_setmana.used.md perquè no
    s'apliqui per error a una edició futura."""
    if not TESI_SETMANA_PATH.exists():
        return
    used_path = TESI_SETMANA_PATH.with_name("tesi_setmana.used.md")
    TESI_SETMANA_PATH.replace(used_path)
    print(f"  Tesi setmanal consumida i marcada com a usada: {used_path.name}")


NOTICIES_EDITOR_PATH = ROOT / "config" / "noticies_editor.md"
HISTORIAL_NOTICIES_PATH = ROOT / "config" / "historial_editorial_noticies.jsonl"


def marcar_noticies_editor_usades() -> None:
    """Renombra config/noticies_editor.md a noticies_editor.used.md perquè
    no s'apliqui per error a una edició futura. Mateix patró que
    marcar_tesi_usada()."""
    if not NOTICIES_EDITOR_PATH.exists():
        return
    used_path = NOTICIES_EDITOR_PATH.with_name("noticies_editor.used.md")
    NOTICIES_EDITOR_PATH.replace(used_path)
    print(f"  Notícies editor consumides i marcades com a usades: {used_path.name}")


def registrar_noticies_editor_usades(candidats: list, borrador: str, semana_str: str) -> None:
    """Detecta quins candidats [EDITOR] (capturats per snapshot.py a
    _meta.json) apareixen citats al borrador final —per la URL, que Sonnet
    manté literal al link del Bloque 2— i els afegeix a
    historial_editorial_noticies.jsonl. Aquest fitxer construeix el perfil
    editorial de l'editor al llarg del temps: quins angles i segments tria
    setmana rere setmana."""
    usats = [c for c in candidats if c.get("url") and c["url"] in borrador]
    if not usats:
        print("  Notícies editor [EDITOR]: cap ha estat citada literalment "
              "al borrador final", file=sys.stderr)
        return
    ara = datetime.now(timezone.utc).isoformat()
    HISTORIAL_NOTICIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORIAL_NOTICIES_PATH.open("a", encoding="utf-8") as f:
        for c in usats:
            f.write(json.dumps({
                "url": c["url"],
                "titular": c.get("titol", ""),
                "angle": c.get("angle", ""),
                "segment": c.get("segment", ""),
                "semana": semana_str,
                "data_us": ara,
            }, ensure_ascii=False) + "\n")
    print(f"  Notícies editor [EDITOR] usades i registrades a l'historial: {len(usats)}")

# Triggers de revisión del sistema anti-repetición (acordados 2026-05-15):
#   - Núm. 3-4 repite ángulos → añadir salvaguarda barata: segunda llamada a Sonnet
#     tipo "novedad check" (¿este ángulo es novedoso vs los N previos? JSON
#     {novedad: bool, razon: str}, ~600 tokens).
#   - Núm. 7-8 sin repeticiones → sistema simple basado solo en instrucción al
#     prompt validado, no tocar.
#   - Núm. 10+ con tracción → considerar similitud por embeddings (Voyage o
#     modelo local) con umbral cosine > 0,85 como bloqueo automático.
# Riesgos asumidos (gestión humana al Nivel C del pipeline, no por sistema):
# "Window edge" (entradas fuera de la ventana de 6) y "cifra repetida"
# semánticamente cuando el valor numérico cambia ligeramente.


def load_historial() -> list:
    """Carga el historial editorial. Devuelve lista vacía si no existe o se
    corrompe — el pipeline sigue funcionando sin memoria editorial."""
    if not HISTORIAL_PATH.exists():
        return []
    try:
        data = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        print(f"  Aviso: {HISTORIAL_PATH.name} no es una lista. Se ignora.", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"  Aviso: {HISTORIAL_PATH.name} corrupto ({e}). Se ignora.", file=sys.stderr)
    return []


def save_historial(entries: list) -> None:
    HISTORIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORIAL_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def format_historial_para_prompt(entries: list, max_n: int = HISTORIAL_VENTANA) -> str:
    if not entries:
        return ""
    recent = entries[-max_n:]
    lines = [
        "EDICIONES RECIENTES — el ángulo de esta edición debe ser distinto:",
        "",
    ]
    for e in recent:
        noticias = "; ".join(e.get("noticias", [])) or "(sin registro)"
        lines.append(
            f"- Núm. {e.get('numero', '?')} ({e.get('semana', '?')}): "
            f"cifra {e.get('cifra', '?')}. "
            f"Ángulo: {e.get('angulo_bloc1', '(sin registro)')}. "
            f"Predicción: {e.get('tema_prediccion', '(sin registro)')}. "
            f"Noticias citadas: {noticias}."
        )
    lines.extend([
        "",
        "Para esta edición, evita tratar de nuevo los ángulos listados. No "
        "basta con cambiar la cifra — busca una dimensión analítica nueva: "
        "si las últimas ediciones han tratado comparativa internacional, "
        "mira concentración interna; si han tratado ocupación, mira "
        "márgenes; si han tratado alimentación, mira moda, restauración o "
        "servicios. La prensa de la semana suele ofrecer múltiples ángulos "
        "— escoge el menos explorado en los historiales anteriores. Está "
        "permitido revisitar un tema si hay novedad sustancial (revisión "
        "de Eurostat, dato confirmatorio, giro estructural), pero el "
        "ángulo principal y la cifra protagonista deben ser frescos.",
    ])
    return "\n".join(lines)


def extract_historial_entry(
    client: "Anthropic", modelo: str, numero: int, semana: str, borrador: str
) -> dict:
    """Segunda llamada barata a Sonnet para extraer los campos del historial.

    Devuelve un dict con numero, semana, cifra, dataset_bloc1, periodo_bloc1,
    angulo_bloc1, tema_prediccion, noticias[3]. dataset_bloc1/periodo_bloc1
    identifican la fuente y el periodo exactos de la cifra protagonista —
    se usan para detectar repetición frente a la edición anterior (ver
    es_dada_repetida). Lanza excepción si el modelo no devuelve JSON
    parseable — el caller la captura y omite la actualización sin romper
    el pipeline.
    """
    prompt = (
        "Has generado esta edición de la newsletter 'El Pulso de la semana':\n\n"
        "<EDICION>\n" + borrador + "\n</EDICION>\n\n"
        "Extrae los siguientes campos y devuelve EXCLUSIVAMENTE un JSON válido "
        "(sin texto adicional, sin code fences):\n\n"
        "{\n"
        '  "cifra": "<la cifra protagonista del bloque 1, p.ej. +4,1%>",\n'
        '  "dataset_bloc1": "<el dataset/indicador exacto del que procede la '
        'cifra protagonista, p.ej. \'ICM real nacional\', \'ICM real por CCAA '
        '- Cataluña\', \'CDMGE grandes cadenas\', \'Productividad - coste '
        'laboral por ocupado\'>",\n'
        '  "periodo_bloc1": "<el periodo exacto de esa cifra, p.ej. 2026-06, '
        'o 2018-2024 si es una serie>",\n'
        '  "angulo_bloc1": "<una frase de 12-20 palabras sintetizando la tesis '
        'editorial del bloque 1>",\n'
        '  "tema_prediccion": "<una frase de 12-20 palabras sintetizando la '
        'predicción del bloque 4, incluyendo el plazo si lo tiene>",\n'
        '  "noticias": [\n'
        '    "<titular exacto de la primera noticia del bloque 2>",\n'
        '    "<titular exacto de la segunda noticia>",\n'
        '    "<titular exacto de la tercera noticia>"\n'
        '  ]\n'
        "}"
    )
    response = client.messages.create(
        model=modelo,
        max_tokens=600,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    data = json.loads(text)
    return {
        "numero": numero,
        "semana": semana,
        "cifra": str(data.get("cifra", "")),
        "dataset_bloc1": str(data.get("dataset_bloc1", "")),
        "periodo_bloc1": str(data.get("periodo_bloc1", "")),
        "angulo_bloc1": str(data.get("angulo_bloc1", "")),
        "tema_prediccion": str(data.get("tema_prediccion", "")),
        "noticias": list(data.get("noticias", [])),
    }


def es_dada_repetida(entry_actual: dict, historial: list, semana_actual: str) -> tuple[bool, str]:
    """¿La cifra protagonista del Bloque 1 repite dataset Y periodo respecto
    a la edición anterior? Compara dataset_bloc1+periodo_bloc1 (no la cifra
    en sí, que puede variar levemente con una revisión de la serie) contra
    la última entrada del historial distinta de la semana actual.

    Devuelve (True, motivo) si coinciden exactamente ambos campos (repetición
    real: mismo indicador Y mismo periodo). Si falta alguno de los dos campos
    en la entrada actual (extracción incompleta) no se considera repetición
    — mejor no bloquear el pipeline por un dato ambiguo.
    """
    previas = [e for e in historial if e.get("semana") != semana_actual]
    if not previas:
        return False, ""
    ultima = previas[-1]
    dataset_actual = str(entry_actual.get("dataset_bloc1", "")).strip().lower()
    periodo_actual = str(entry_actual.get("periodo_bloc1", "")).strip().lower()
    if not dataset_actual or not periodo_actual:
        return False, ""
    dataset_prev = str(ultima.get("dataset_bloc1", "")).strip().lower()
    periodo_prev = str(ultima.get("periodo_bloc1", "")).strip().lower()
    if dataset_actual == dataset_prev and periodo_actual == periodo_prev:
        return True, (
            f"la cifra protagonista repite el dataset '{entry_actual.get('dataset_bloc1')}' "
            f"y el periodo '{entry_actual.get('periodo_bloc1')}' ya usados en la edición "
            f"Núm. {ultima.get('numero', '?')} ({ultima.get('semana', '?')})"
        )
    return False, ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", required=True, help="Fecha del lunes (YYYY-MM-DD)")
    p.add_argument("--numero", type=int, required=True, help="Número de edición")
    p.add_argument("--force", action="store_true", help="Sobrescribir newsletter.md si existe")
    p.add_argument("--no-historial", action="store_true",
                   help="No leer ni actualizar el historial editorial")
    p.add_argument("--context-extra", default="",
                   help="Bloc de context addicional (p.ex. fet macro) que s'injecta "
                        "al prompt just abans de <RECOPILACION_PRENSA>")
    p.add_argument("--titular", default="",
                   help="Titular fix (mode P2). Si buit, el mode es detecta "
                        "automàticament a partir de les actualitzacions del snapshot.")
    p.add_argument("--bloc3", default="",
                   choices=["", "europeu", "cdmge_tasa_anual", "editorial_contexto",
                            "icm_ramas", "marges_branca", "icm_distribucio", "icm_ccaa"],
                   help="Sobreescriu la selecció automàtica del bloc 3. "
                        "'marges_branca' només és vàlid si el dataset de marges "
                        "està verificat (verificat=True al snapshot). 'icm_ccaa' "
                        "només és vàlid si pulso_icm.csv té desglossament per CCAA.")
    return p.parse_args()


def cargar_templates() -> tuple[str, str, str]:
    linea = (ROOT / "templates" / "linea_editorial.md").read_text(encoding="utf-8")
    estil = (ROOT / "config" / "estil_editorial.md").read_text(encoding="utf-8")
    diccionario = (ROOT / "templates" / "data_dictionary.md").read_text(encoding="utf-8")
    return linea, estil, diccionario


def slice_cdmge(csv_path: Path, dias: int = 60) -> str:
    """Últimos `dias` días del CDMGE en formato CSV compacto."""
    df = pd.read_csv(csv_path, parse_dates=["data"])
    cutoff = df["data"].max() - pd.Timedelta(days=dias)
    df = df[df["data"] >= cutoff].sort_values(["indicador", "data"])
    lines = ["fecha,indicador,valor"]
    for _, row in df.iterrows():
        lines.append(f"{row['data'].strftime('%Y-%m-%d')},{row['indicador']},{row['valor']}")
    return "\n".join(lines)


def slice_europa(csv_path: Path, meses: int = 24) -> str:
    """Últimos `meses` periodos para todos los países disponibles."""
    df = pd.read_csv(csv_path)
    periodos = sorted(df["periode"].unique())[-meses:]
    df = df[df["periode"].isin(periodos)].sort_values(["pais", "periode"])
    return df.to_csv(index=False)


def max_periodo_europeo(csv_path: Path) -> str:
    """Periodo más reciente (YYYY-MM) disponible en el CSV europeo (Eurostat)."""
    return str(pd.read_csv(csv_path, usecols=["periode"])["periode"].max())


def detectar_novetat_eurostat(periodo_actual: str, historial: list, semana_actual: str) -> bool:
    """¿Eurostat ha publicado un periodo nuevo desde la última edición?"""
    previas = [e for e in historial if e.get("semana") != semana_actual]
    if not previas:
        return True
    ultimo = previas[-1].get("periodo_eurostat")
    if not ultimo:
        return True
    return periodo_actual > str(ultimo)


def slice_cdmge_dias_clave(csv_path: Path) -> tuple[str, str]:
    """tasa_anual en los días clave (14, 18, 22, 26, 30/último) del mes más reciente."""
    df = pd.read_csv(csv_path, parse_dates=["data"])
    ta = df[df["indicador"] == "tasa_anual"].sort_values("data")
    ult = ta["data"].max().to_period("M")
    mes = ta[ta["data"].dt.to_period("M") == ult].copy()
    mes["dia"] = mes["data"].dt.day
    objetivos, sel, vistos = [14, 18, 22, 26, 30], [], set()
    for obj in objetivos:
        cand = mes[mes["dia"] <= obj]
        if cand.empty:
            continue
        fila = cand.iloc[-1]
        dia = int(fila["dia"])
        if dia in vistos:
            continue
        vistos.add(dia)
        sel.append((dia, float(fila["valor"])))
    lines = ["dia,tasa_anual"] + [f"{d},{v}" for d, v in sel]
    return str(ult), "\n".join(lines)


def eurostat_lag_setmanes(periodo_actual: str, semana_str: str) -> int:
    """Setmanes de retard entre el darrer periode Eurostat i la data d'enviament."""
    from datetime import date as _date
    y, m = int(periodo_actual[:4]), int(periodo_actual[5:7])
    last_day = 28 if m == 2 else (30 if m in (4, 6, 9, 11) else 31)
    fi_periode = _date(y, m, last_day)
    enviament = _date.fromisoformat(semana_str)
    return max(0, (enviament - fi_periode).days // 7)


def cdmge_dies_mes_actual(csv_path: Path) -> int:
    """Nombre de dies disponibles (files úniques de tasa_anual) al mes més recent del CDMGE."""
    df = pd.read_csv(csv_path, parse_dates=["data"])
    ta = df[df["indicador"] == "tasa_anual"].sort_values("data")
    if ta.empty:
        return 0
    ult = ta["data"].max().to_period("M")
    return int((ta["data"].dt.to_period("M") == ult).sum())


# ---- DATASETS ESTRUCTURALS (nous) ----

def slice_productivitat(csv_path: Path) -> str:
    """Costos laborals i productivitat anual del comerç minorista espanyol."""
    df = pd.read_csv(csv_path)
    cols = [
        "any", "cost_laboral_per_ocupat", "cost_laboral_hora",
        "quota_salarial", "marge_brut", "productivitat_va_hora",
        "gastos_personal_constants",
    ]
    available = [c for c in cols if c in df.columns]
    return df[available].sort_values("any").to_csv(index=False)


def slice_ocupacio_spain(csv_path: Path) -> str:
    """Ocupació del comerç minorista a Espanya (total, últims 8 anys)."""
    df = pd.read_csv(csv_path)
    esp = df[(df["pais_codi"] == "ES") & (df["sex"] == "T")].copy()
    anys = sorted(esp["any"].unique())[-8:]
    result = (
        esp[esp["any"].isin(anys)][["any", "edat", "ocupats_milers"]]
        .sort_values(["any", "edat"])
    )
    return result.to_csv(index=False)


def slice_ipc(csv_path: Path, mesos: int = 24) -> str:
    """Últims mesos de l'IPC."""
    df = pd.read_csv(csv_path).sort_values(["any", "mes"])
    return df.tail(mesos).to_csv(index=False)


ICM_BRANCA_GENERAL = "Comercio al por menor, excepto de vehículos de motor y motocicletas"

# Etiquetes curtes per a les branques de l'ICM (estalvia tokens al prompt).
ICM_BRANCA_CURTA = {
    "Comercio al por menor, excepto de vehículos de motor y motocicletas": "Total CNAE 47",
    "Comercio al por menor sin Estaciones de Servicio (47 sin 473)": "47 sin combustible",
    "Comercio al por menor de productos alimenticios, bebidas y tabaco en establecimientos especializados": "Alimentación especializada",
    "Comercio al por menor en establecimientos no especializados": "No especializado (súper/hiper)",
    "Comercio al por menor en establecimientos no especializados, con predominio en productos alimenticios, bebidas y tabaco": "No especializado alimentación",
    "Otro comercio al por menor en establecimientos no especializados": "No especializado no alim.",
    "Comercio al por menor de equipos para las tecnologías de la información y las comunicaciones en establecimientos especializados": "Equipos TIC",
    "Comercio al por menor de otros artículos de uso doméstico en establecimientos especializados": "Equipamiento del hogar",
    "Comercio al por menor de artículos culturales y recreativos en establecimientos especializados": "Cultura y ocio",
    "Comercio al por menor de otros artículos en establecimientos especializados": "Otros especializados",
    "Comercio al por menor de combustible para la automoción en establecimientos especializados": "Combustible",
    "Comercio al por menor en puestos de venta y en mercadillos": "Mercadillos",
    "Comercio al por menor por correspondencia o Internet": "Correo/Internet",
    "Comercio al por menor no realizado ni en establecimientos, ni en puestos de venta ni en mercadillos": "Fuera de establecimiento",
}


def slice_icm(csv_path: Path, mesos: int = 15) -> str:
    """Formata el pulso_icm.csv per al prompt en dos blocs compactes:
      1. Sèrie general (CNAE 47) mes a mes: var. anual i acumulada,
         nominal i real (constants) — mostra el gir a negatiu.
      2. Desglossament per branca del mes més recent (real, var. anual).

    Filtra sempre ambit == "nacional": pulso_icm.csv també conté el
    desglossament per CCAA (mateixa branca general, ambit = nom de la
    comunitat) que consumeix slice_icm_ccaa() — cal excloure'l aquí per no
    barrejar-lo amb la sèrie i el desglossament nacionals.
    """
    df = pd.read_csv(csv_path, parse_dates=["data"])
    df = df[df["ambit"] == "nacional"].copy()
    df["periode"] = df["data"].dt.strftime("%Y-%m")

    # ── Bloc 1: sèrie general mes a mes ──
    gen = df[df["branca"] == ICM_BRANCA_GENERAL].copy()
    piv = gen.pivot_table(index="periode", columns=["tipus", "indicador"],
                          values="valor", aggfunc="first")
    piv = piv.tail(mesos)
    piv.columns = [f"{t}_{i}" for t, i in piv.columns]
    prefer = ["real_var_anual", "nominal_var_anual",
              "real_var_mitjana_acum", "nominal_var_mitjana_acum",
              "real_index", "nominal_index"]
    cols = [c for c in prefer if c in piv.columns] + \
           [c for c in piv.columns if c not in prefer]
    linia1 = ("Serie general (Comercio al por menor total, CNAE 47) · "
              "variacion interanual y acumulada, precios corrientes (nominal) "
              "y constantes (real):\n" + piv[cols].round(1).to_csv())

    # ── Bloc 2: branques del mes més recent ──
    ult = df["data"].max()
    br = df[(df["data"] == ult) & (df["tipus"] == "real") &
            (df["indicador"] == "var_anual") &
            (df["branca"] != ICM_BRANCA_GENERAL)].copy()
    br["etiqueta"] = br["branca"].map(ICM_BRANCA_CURTA).fillna(br["branca"])
    br = br[["etiqueta", "valor"]].sort_values("valor", ascending=False)
    linia2 = (f"\nDesglose por rama · variacion interanual real · "
              f"{ult.strftime('%Y-%m')} (mes mas reciente):\n" +
              br.round(1).to_csv(index=False))

    return linia1 + linia2


# Etiquetes curtes per als noms de CCAA de l'INE (format oficial invertit,
# p.ex. "Rioja, La") a format llegible per a la newsletter.
ICM_CCAA_CURTA = {
    "Rioja, La": "La Rioja",
    "Navarra, Comunidad Foral de": "Navarra",
    "Murcia, Región de": "Murcia",
    "Madrid, Comunidad de": "Madrid",
    "Castilla - La Mancha": "Castilla-La Mancha",
    "Balears, Illes": "Illes Balears",
    "Asturias, Principado de": "Asturias",
}


def icm_ccaa_disponible(csv_path: Path) -> bool:
    """¿pulso_icm.csv conté desglossament per CCAA (ambit != nacional)?
    Necessari perquè el snapshot pot ser d'abans que snapshot.py capturés
    aquesta dimensió, o si la font no la publica aquell periode."""
    if not csv_path.exists():
        return False
    df = pd.read_csv(csv_path, usecols=["ambit"])
    return bool((df["ambit"] != "nacional").any())


def slice_icm_ccaa(csv_path: Path) -> str:
    """Desglossament per CCAA de pulso_icm.csv (real, var_anual, branca
    general, mes més recent disponible per a aquesta dimensió), ordenat de
    major creixement a major caiguda. Mateix patró que el desglossament per
    branca de slice_icm(), amb 'ambit' (CCAA) com a dimensió."""
    df = pd.read_csv(csv_path, parse_dates=["data"])
    ccaa = df[(df["ambit"] != "nacional") & (df["tipus"] == "real") &
              (df["indicador"] == "var_anual")].copy()
    if ccaa.empty:
        return ""
    ult = ccaa["data"].max()
    ccaa = ccaa[ccaa["data"] == ult].copy()
    ccaa["etiqueta"] = ccaa["ambit"].map(ICM_CCAA_CURTA).fillna(ccaa["ambit"])
    ccaa = ccaa[["etiqueta", "valor"]].sort_values("valor", ascending=False)
    return (f"Desglose por Comunidad Autonoma (CCAA) · variacion interanual real · "
            f"{ult.strftime('%Y-%m')} (mes mas reciente):\n" +
            ccaa.round(1).to_csv(index=False))


def slice_icm_distribucio(csv_path: Path, mesos: int = 15) -> str:
    """Formata pulso_icm_distribucio.csv per al prompt en dos blocs:
      1. Sèrie real var_anual pivotada per mode de distribució (Grandes
         Superficies, Grandes cadenas, Pequeñas cadenas, Empresas
         unilocalizadas), últims `mesos` mesos — mostra si la divergència
         entre modes és estructural o puntual.
      2. Desglossament del mes més recent, ordenat de major a menor.
    """
    df = pd.read_csv(csv_path, parse_dates=["data"])
    df["periode"] = df["data"].dt.strftime("%Y-%m")
    real = df[(df["tipus"] == "real") & (df["indicador"] == "var_anual")].copy()

    piv = real.pivot_table(index="periode", columns="modo", values="valor", aggfunc="first")
    piv = piv.tail(mesos)
    linia1 = ("Variacion interanual real por modo de distribucion · "
              f"ultimos {mesos} meses:\n" + piv.round(1).to_csv())

    ult = df["data"].max()
    desglose = real[real["data"] == ult][["modo", "valor"]].sort_values("valor", ascending=False)
    linia2 = (f"\nDesglose del mes mas reciente ({ult.strftime('%Y-%m')}):\n" +
              desglose.round(1).to_csv(index=False))
    return linia1 + linia2


def detectar_novetat_icm_distribucio(periodo_actual: str, historial: list, semana_actual: str) -> bool:
    """¿icm_distribucio té un periode que no s'ha usat encara a cap edició
    prèvia registrada? Mateix patró que detectar_novetat_eurostat: si cap
    entrada prèvia té el camp (primer cop que es capta el dataset), es
    considera novetat."""
    previas = [e for e in historial if e.get("semana") != semana_actual]
    if not previas:
        return True
    ultimo = previas[-1].get("periodo_icm_distribucio")
    if not ultimo:
        return True
    return periodo_actual > str(ultimo)


# Frases que, si apareixen a config/tesi_setmana.md, indiquen que l'editor
# demana una comparativa territorial (per CCAA) al Bloc 3. Es comprova en
# minúscules, com a substring — no cal que siguin paraules senceres.
TRIGGERS_TERRITORIAL = [
    "ccaa", "comunitat autònoma", "comunitats autònomes", "comunitat autonoma",
    "comunidad autónoma", "comunidad autonoma", "comunidades autónomas",
    "comunidades autonomas", "comparativa territorial", "divergència territorial",
    "divergencia territorial", "per territoris", "por territorios",
    "entre ccaa", "entre comunidades", "entre comunitats", "per comunitats",
    "por comunidades",
]


def tesi_demana_comparativa_territorial(tesi_text: str) -> bool:
    """¿La tesi setmanal (config/tesi_setmana.md) demana explícitament una
    comparativa territorial (CCAA) al Bloc 3? Si és així, el mode 'icm_ccaa'
    s'activa automàticament (si hi ha dades disponibles), per davant dels
    criteris de novetat de la resta de modes: la intenció editorial explícita
    mana sobre l'heurística de frescor de dades."""
    if not tesi_text:
        return False
    t = tesi_text.lower()
    return any(trigger in t for trigger in TRIGGERS_TERRITORIAL)


def slice_marges(csv_path: Path) -> str:
    """Marge sobre vendes (%) per branca comercial, pivotat branca × any.

    Pensat per creuar-lo amb l'ICM (vendes per branca): quines branques creixen
    en vendes però perden marge, i a l'inrevés. Font INE, Encuesta Anual de
    Comercio (EEE Comercio); marge = EBE/vendes, sèrie anual estructural."""
    df = pd.read_csv(csv_path)
    piv = df.pivot_table(index="branca", columns="any",
                         values="marge_vendes_pct", aggfunc="first")
    piv = piv.reindex(sorted(piv.columns), axis=1)
    return ("Marge sobre vendes (%) per branca del comerç minorista · "
            "anys disponibles:\n" + piv.round(1).to_csv())


# ---- DETECCIÓ DE MODE EDITORIAL ----

def detectar_mode_editorial(
    historial: list,
    semana_str: str,
    meta: dict,
) -> tuple[str, str]:
    """Retorna (mode, motiu): 'P1' si hi ha dataset nou, 'P2' si no.

    P1: algun dataset clau ha rebut actualització nova vs l'última edició.
    P2: cap novetat; la tesi editorial ha de manar (editor fixa --titular).
    """
    previes = [e for e in historial if e.get("semana") != semana_str]
    if not previes:
        return "P1", "primera edició, sense historial de comparació"

    ultima = previes[-1]

    # ICM: nou mes de la sèrie oficial de vendes minoristes (indicador de
    # titular de l'INE). Prioritari sobre la resta perquè és la mesura canònica
    # del pols del sector. Si l'entrada anterior no registrava ICM (font nova al
    # pipeline), un ICM disponible ja compta com a novetat que mana.
    periodo_icm = meta.get("icm", {}).get("ultimo_periodo", "")
    prev_icm = ultima.get("periodo_icm")
    if periodo_icm and (prev_icm is None or periodo_icm > str(prev_icm)):
        return "P1", f"ICM nou mes {periodo_icm} (anterior: {prev_icm or 'sense registre'})"

    # Eurostat: nou periode mensual
    periodo_eurostat = meta.get("pulso_europeo", {}).get("ultimo_periodo", "")
    prev_eurostat = str(ultima.get("periodo_eurostat", ""))
    if periodo_eurostat and periodo_eurostat > prev_eurostat:
        return "P1", f"Eurostat nou periode {periodo_eurostat} (anterior: {prev_eurostat})"

    # Productivitat: nou any (només si l'entrada anterior ja tenia el camp)
    prod_any = meta.get("productivitat", {}).get("ultimo_any", 0)
    prev_prod_any = ultima.get("productivitat_any")
    if prev_prod_any is not None and prod_any > prev_prod_any:
        return "P1", f"Productivitat nou any {prod_any} (anterior: {prev_prod_any})"

    # Ocupació: nou any (ídem)
    ocup_any = meta.get("ocupacio", {}).get("ultimo_any", 0)
    prev_ocup_any = ultima.get("ocupacio_any")
    if prev_ocup_any is not None and ocup_any > prev_ocup_any:
        return "P1", f"Ocupació nou any {ocup_any} (anterior: {prev_ocup_any})"

    return "P2", "cap actualització significativa detectada"


# ---- CONSTRUCCIÓ DEL PROMPT ----

def construir_prompts(
    semana_dir: Path,
    semana_str: str,
    numero: int,
    linea_editorial: str,
    estil_editorial: str,
    diccionario: str,
    historial_entries: list,
    bloc3_mode: str = "europeu",
    context_extra: str = "",
    periodo_actual: str = "",
    mode_editorial: str = "P1",
    titular: str = "",
    marges_disponible: bool = False,
    hi_ha_noticies_editor: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Construye (system, messages) para la llamada al modelo.

    mode_editorial: 'P1' (dada fresca mana) o 'P2' (tesi mana, dada explica).
    titular: fixat en mode P2; buit en P1.
    bloc3_mode: 'europeu', 'cdmge_tasa_anual', 'editorial_contexto',
        'icm_ramas', 'marges_branca' o 'icm_distribucio'.
    marges_disponible: injecta <MARGES_BRANCA> al prompt només si és True (el
        dataset de marges existeix al snapshot I té verificat=True).
    hi_ha_noticies_editor: si és True, afegeix la regla 9bis que demana
        prioritzar les notícies marcades [EDITOR] a <RECOPILACION_PRENSA>.
    """

    cdmge_data = slice_cdmge(semana_dir / "pulso_diario.csv", dias=60)
    prensa = (semana_dir / "recopilacion_prensa.md").read_text(encoding="utf-8")
    meta = (semana_dir / "_meta.json").read_text(encoding="utf-8")

    # ---- Bloque 3 (D.) — tres modes, sense canvis ----
    if bloc3_mode == "cdmge_tasa_anual":
        bloque3_instr = (
            "D. Bloque 3, estructura literal (RITMO INTRAMENSUAL — Eurostat sin "
            "periodo nuevo esta semana):\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   **Datos:** Ritmo de ventas de grandes cadenas · últimos 30 días\n\n"
            "   - Día 14: <valor>%\n"
            "   - Día 18: <valor>%\n"
            "   - Día 22: <valor>%\n"
            "   - Día 26: <valor>%\n"
            "   - Día 30: <valor>%\n\n"
            "   <2-3 párrafos interpretando la aceleración o desaceleración del "
            "ritmo de ventas DENTRO del mes>\n\n"
            "   Usa EXACTAMENTE los días y los valores de tasa_anual de "
            "<PULSO_CDMGE_DIAS_CLAVE>. El subtítulo **Datos:** debe ser, literal, "
            "'Ritmo de ventas de grandes cadenas · últimos 30 días'. MANTÉN EL "
            "ORDEN CRONOLÓGICO (día 1 → último día); NO ordenes por valor. La "
            "tasa anual está acumulada dentro del mes: los primeros días, con "
            "pocos días acumulados, son volátiles; la señal fiable es la "
            "tendencia hacia el cierre del mes."
        )
    elif bloc3_mode == "icm_ramas":
        bloque3_instr = (
            "D. Bloque 3, estructura literal (DESGLOSE ICM POR RAMAS — muestra la "
            "polarización dentro del sector):\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   **Datos:** Ventas minoristas por rama · <mes> (variación real)\n\n"
            "   - Rama 1: <valor>%\n"
            "   - Rama 2: <valor>%\n"
            "   - ...\n\n"
            "   <2-3 párrafos interpretando qué ramas caen y cuáles resisten, "
            "conectando con la contracción general del Bloque 1>\n\n"
            "   Usa el 'Desglose por rama' de <PULSO_ICM_INE> (variación interanual "
            "real del mes más reciente). Selecciona 5-8 ramas relevantes que muestren "
            "el contraste (algunas en negativo, otras en positivo). compose.py las "
            "renderiza como barras divergentes (positivo azul, negativo rojo). "
            "Ordena de mayor a menor valor. El subtítulo debe llevar el mes y la "
            "palabra 'real', sin 'variación interanual' (compose.py añade la leyenda)."
        )
    elif bloc3_mode == "icm_ccaa":
        bloque3_instr = (
            "D. Bloque 3, estructura literal (DESGLOSE ICM POR CCAA — muestra la "
            "divergencia territorial dentro del sector):\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   **Datos:** Ventas minoristas por Comunidad Autónoma · <mes> (variación real)\n\n"
            "   - Comunidad 1: <valor>%\n"
            "   - Comunidad 2: <valor>%\n"
            "   - ...\n\n"
            "   <2-3 párrafos interpretando qué comunidades crecen y cuáles caen, "
            "conectando con la tesis territorial del Bloque 1: la divergencia entre "
            "CCAA no es ruido, responde a estructura de mercado laboral, base "
            "industrial y renta disponible real.>\n\n"
            "   Usa el 'Desglose por Comunidad Autonoma (CCAA)' de <PULSO_ICM_CCAA> "
            "(variación interanual real del mes más reciente disponible para esta "
            "dimensión). Incluye TODAS las CCAA disponibles (compose.py las renderiza "
            "como barras divergentes, positivo azul, negativo rojo). Ordena de mayor a "
            "menor valor. El subtítulo debe llevar el mes y la palabra 'real', sin "
            "'variación interanual' (compose.py añade la leyenda)."
        )
    elif bloc3_mode == "icm_distribucio":
        bloque3_instr = (
            "D. Bloque 3, estructura literal (ICM POR MODO DE DISTRIBUCIÓN — "
            "muestra qué tipo de operador gana o pierde volumen):\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   **Datos:** Ventas minoristas por modo de distribución · <mes> (variación real)\n\n"
            "   - Grandes cadenas: <valor>%\n"
            "   - Empresas unilocalizadas: <valor>%\n"
            "   - Pequeñas cadenas: <valor>%\n"
            "   - Grandes Superficies: <valor>%\n\n"
            "   <2-3 párrafos interpretando qué modo de distribución gana o "
            "pierde volumen, conectando con la divergencia de formatos del "
            "Bloque 1: los operadores unilocalizados y las grandes cadenas "
            "especializadas suelen capturar mejor los formatos que han "
            "redefinido su propuesta de valor, mientras las grandes "
            "superficies generalistas sienten más la presión.>\n\n"
            "   Usa EXCLUSIVAMENTE los 4 modos del 'Desglose del mes más "
            "reciente' de <PULSO_ICM_DISTRIBUCIO> (variación interanual real). "
            "compose.py los renderiza como barras divergentes. Ordena de mayor "
            "a menor valor. El subtítulo debe llevar el mes y la palabra "
            "'real', sin 'variación interanual' (compose.py añade la leyenda)."
        )
    elif bloc3_mode == "marges_branca":
        bloque3_instr = (
            "D. Bloque 3, estructura literal (MÁRGENES POR RAMA — rentabilidad "
            "estructural del comercio minorista):\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   **Datos:** Margen sobre ventas por rama · <año más reciente>\n\n"
            "   - Rama 1: <valor>%\n"
            "   - Rama 2: <valor>%\n"
            "   - ...\n\n"
            "   <2-3 párrafos con el ángulo editorial: cruza el margen de "
            "<MARGES_BRANCA> con el crecimiento de ventas por rama de <PULSO_ICM_INE>. "
            "Busca la disociación: ¿qué ramas CRECEN en ventas pero PIERDEN margen "
            "(volumen a costa de rentabilidad), y cuáles hacen lo contrario "
            "(menos ventas pero más margen)? Ese contraste es la tesis del bloque.>\n\n"
            "   Usa EXCLUSIVAMENTE los valores de <MARGES_BRANCA>. Selecciona 5-8 ramas "
            "que muestren el contraste. Ordena de mayor a menor margen. compose.py las "
            "renderiza como barras. El subtítulo debe llevar el año, sin 'variación'. "
            "IMPORTANTE: la fuente es el INE (Encuesta Anual de Comercio); el margen es "
            "el excedente bruto de explotación sobre ventas. Cítala como 'el INE' en el "
            "cuerpo, nunca el código técnico ni el número de tabla."
        )
    elif bloc3_mode == "editorial_contexto":
        bloque3_instr = (
            "D. Bloque 3, estructura literal (CONTEXTO EDITORIAL — inicio de mes, "
            "menos de 10 días de datos CDMGE disponibles y Eurostat sin periodo "
            "nuevo):\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   <2-3 párrafos de lectura editorial sobre tendencias recientes del "
            "sector. Apóyate en los datos del mes anterior de <PULSO_DIARIO_CDMGE> "
            "(ya consolidados; evita el mes en curso, que con pocos días acumulados "
            "es provisional y volátil). "
            "NO incluyas subtítulo 'Datos:' ni lista de cifras — este bloque es "
            "lectura editorial sin gráfico. "
            "Lectura estructural por encima de la coyuntural: busca el patrón "
            "(concentración, polarización, márgenes, eficiencia), no el dato puntual."
        )
    else:  # "europeu"
        bloque3_instr = (
            "D. Bloque 3, estructura literal:\n\n"
            "   **◆ DATOS DE LA SEMANA**\n\n"
            "   **Datos:** <subtítulo descriptivo SIN 'variación interanual', "
            "p.ej. Ventas minoristas marzo 2026>\n\n"
            "   - País 1: <valor>%\n"
            "   - País 2: <valor>%\n"
            "   - ...\n\n"
            "   <2-3 párrafos de interpretación>\n\n"
            "   Selecciona 4-8 países o categorías relevantes. compose.py renderiza "
            "la lista como barras divergentes (positivo azul, negativo rojo). "
            "Ordena la lista de mayor a menor valor."
        )

    # ---- Bloque 1 (B.) — condicional al mode ----
    if mode_editorial == "P2":
        bloque1_instr = (
            "B. Bloque 1, estructura literal (MODE P2 — tesi primer, dada com a suport):\n\n"
            "   **◆ LA CIFRA DE LA SEMANA**\n\n"
            "   **El dato:** <xifra que evidencia la tesi, "
            "p.ex. +32% cost laboral per ocupat 2018-2024>\n"
            "   **Contexto:** <descripció breu sense nota de frescor, "
            "p.ex. Costos laborals del comerç minorista · Espanya 2018-2024>\n"
            "   **Fuente:** <font legible sense codi tècnic, "
            "p.ex. Comptabilitat d'empreses · INE>\n\n"
            "   La dada ha de provenir d'un dataset propi del Observatori (regla 8). "
            "En mode P2, prioritza productivitat.csv (cost_laboral_per_ocupat, "
            "quota_salarial, marge_brut), ocupacio_comerc.csv o ipc.csv si suporta "
            "la tesi. Usa pulso_diario.csv o pulso_europeo.csv només si son el "
            "millor argument disponible per al Titular.\n\n"
            "   Estructura dels paràgrafs:\n"
            "   - 1r paràgraf: enuncia la tesi afirmativa (el Titular en forma "
            "d'argument). Veu assertiva, no descriptiva.\n"
            "   - 2n-3r paràgraf: evidència estructural que la suporta. "
            "No com a notícia de frescor; com a patró de fons que el lector pot "
            "verificar al dashboard del Observatori.\n\n"
        )
    else:  # P1
        bloque1_instr = (
            "B. Bloque 1, estructura literal (MODE P1 — dada fresca mana):\n\n"
            "   **◆ LA CIFRA DE LA SEMANA**\n\n"
            "   **Cifra:** <p.ej. +4,1%>\n"
            "   **Contexto:** <descripción breve, "
            "p.ej. Ventas minoristas España · marzo 2026>\n"
            "   **Fuente:** <descripción + fuente sin códigos, "
            "p.ej. Variación interanual · Eurostat>\n\n"
            "   La cifra protagonista procede del dataset amb actualització nova "
            "aquest periode (regla absoluta 8). "
            "El Titular ha de derivar-se d'aquesta dada i la seva lectura.\n\n"
            "   <2-3 párrafos de lectura editorial con la conclusión firmada>\n\n"
        )

    # ---- Regles 10 i 12 — condicionals al mode ----
    if mode_editorial == "P1":
        rule_10 = (
            "10. Cuando la cifra protagonista del Bloque 1 procede de pulso_diario.csv "
            "(CDMGE, indicador del INE sobre grandes cadenas de distribución), incluye "
            "siempre en el Bloque 1: (a) la fecha exacta del dato más reciente, que "
            "encontrarás en <META_SNAPSHOT> bajo pulso_diario.ultima_fecha; y (b) la "
            "nota literal: 'Dato más reciente disponible a [fecha]. El indicador del "
            "INE sobre grandes cadenas se publica con un desfase habitual de 30 días.' "
            "Puede ir en el campo Fuente: o integrada en el cuerpo, pero no puede "
            "omitirse.\n"
        )
        rule_12 = (
            "12. La cifra protagonista del Bloque 1 debe ser lo más reciente posible. "
            "Si en <AVISO_FRESCOR_DADES> se indica que el dato Eurostat tiene un "
            "retard superior a 7 setmanes respecte la data d'enviament, la cifra del "
            "Bloque 1 DEBE proceder del CDMGE (pulso_diario.csv), no de Eurostat. "
            "Eurostat puede aparecer como dato de contexto en el Bloque 3, "
            "pero no como cifra protagonista del Bloque 1.\n\n"
        )
    else:  # P2
        rule_10 = (
            "10. En mode P2, la dada del Bloque 1 és evidència estructural, no notícia. "
            "NO incloguis la nota 'Dato más reciente disponible a...': és innecessària "
            "quan la dada s'usa com a argument, no com a última lectura publicada. "
            "El camp Fuente: indica la font legible (INE, Eurostat, etc.) però "
            "sense referència temporal de frescor.\n"
        )
        rule_12 = (
            "12. En mode P2, la frescor de la dada NO és un criteri de selecció. "
            "Tria la dada que millor argumenta el Titular, fins i tot si és "
            "d'un any anterior. Productivitat, costos laborals i ocupació solen "
            "ser més adequats per a tesis estructurals que les vendes (CDMGE/Eurostat).\n\n"
        )

    regla_editor = (
        "9bis. Las noticias marcadas con [EDITOR] en <RECOPILACION_PRENSA> han sido "
        "seleccionadas por el editor y deben priorizarse para el Bloque 2. Si hay tres "
        "o más CON CONTENIDO REAL (ver regla 9ter), úsalas todas. Si hay menos de "
        "tres, completa con las mejores del snapshot siguiendo el criterio de "
        "diversidad de fuentes y segmentos (regla 9). Respeta el ángulo editorial "
        "indicado junto a cada noticia [EDITOR] al redactar su lectura.\n"
        "9ter. Una noticia [EDITOR] SOLO puede usarse si su entrada en "
        "<RECOPILACION_PRENSA> incluye una línea '- Snippet:' con texto real. Si una "
        "entrada [EDITOR] no tiene esa línea, o su título es literalmente una URL "
        "(señal de que el fetch de la fuente falló), esa noticia NO tiene contenido "
        "verificado: ignórala por completo —no la cites, no inventes su contenido a "
        "partir de la URL o del ángulo editorial— y elige en su lugar una noticia "
        "normal del snapshot, respetando la regla 9 (diversidad de medios) y la "
        "regla 11 (proximitat) si aplica. Advierte en TRAZABILIDAD qué notícia "
        "[EDITOR] se ha descartado y por qué.\n"
    ) if hi_ha_noticies_editor else ""

    system = [
        {
            "type": "text",
            "text": (
                "Eres el redactor editorial de la newsletter 'El Pulso de la semana' del "
                "Observatorio del Comercio J3B3. Generas el borrador completo de una "
                "edición semanal en Markdown, siguiendo estrictamente la línea editorial "
                "y el diccionario de datos que recibes a continuación.\n\n"
                "Reglas absolutas, sin excepción:\n"
                "1. Cada cifra que cites debe provenir de los datos de la semana que recibirás "
                "en el mensaje del usuario. Nunca inventes cifras.\n"
                "2. Cada noticia que cites debe aparecer en la recopilación de prensa "
                "adjunta, con el titular, medio y fecha exactos.\n"
                "3. Nunca reutilices cifras o noticias de las ediciones modelo del "
                "documento de línea editorial: son ilustrativas, no fácticas.\n"
                "4. Sigue la estructura editorial fija (§3 de la línea editorial).\n"
                "5. No cites códigos técnicos, números de tabla ni precisiones "
                "metodológicas en el cuerpo de los bloques (ver §4 del diccionario de "
                "datos). Solo 'Eurostat', 'INE' o el nombre legible del medio.\n"
                "6. Acaba siempre con la sección '### TRAZABILIDAD (no se envía)' "
                "rastreando cada cifra y noticia a su origen, incluyendo la confirmación "
                "literal: 'Confirmo que no se ha reutilizado ninguna cifra ni noticia "
                "de las ediciones modelo del documento de línea editorial.'\n"
                "7. Devuelve solo el Markdown del borrador, sin envoltura ni comentarios "
                "previos. El primer carácter de la respuesta debe ser '**Asunto:**'.\n"
                "8. La cifra protagonista del Bloque 1 debe proceder SIEMPRE de un dataset "
                "propio del Observatorio: cualquiera de los bloques de datos <PULSO_...>, "
                "<PRODUCTIVITAT_SECTOR>, <OCUPACIO_SECTOR> o <IPC_COMERC> del mensaje. "
                "NUNCA puede proceder de <RECOPILACION_PRENSA>: un dato de prensa no es "
                "fuente primaria del Bloque 1, porque el lector debe poder verificar la "
                "cifra directamente en el Observatorio. Ejemplo de violación de esta regla: "
                "usar un dato de e-commerce (+X%) citado en un artículo de prensa aunque "
                "el artículo cite al CNMC o a un organismo oficial — si ese dato no aparece "
                "en pulso_diario.csv ni en los otros CSVs del snapshot, es dato de prensa, "
                "no del Observatorio. Ponlo en el Bloque 2 como noticia comentada.\n"
                "8bis. <PULSO_ICM_INE> (Índice de Comercio al por Menor del INE) es el "
                "indicador OFICIAL de referencia de las ventas del comercio minorista "
                "español en su conjunto — es la cifra de titular que publica el INE cada "
                "mes. Su variación interanual a precios constantes (real) es la medida "
                "canónica del pulso del sector. Cuando el ICM tiene un mes fresco, es la "
                "fuente PREFERENTE para la cifra protagonista del Bloque 1 frente al CDMGE "
                "(pulso_diario.csv), que mide solo grandes cadenas y actúa como suelo del "
                "ciclo, no como media sectorial. Usa el CDMGE como contraste (grandes "
                "cadenas vs conjunto del sector), no como protagonista, si el ICM está "
                "disponible y es más reciente o igual de reciente.\n"
                "9. Las tres noticias del Bloque 2 deben proceder de medios DISTINTOS: no "
                "repitas dos titulares del mismo medio en la misma edición. Si la "
                "recopilación de prensa solo trae noticias de uno o dos medios, elige "
                "las tres con mayor diversidad de fuente posible y adviértelo en "
                "TRAZABILIDAD.\n"
                + regla_editor
                + rule_10
                + "11. El Bloque 2 debe incluir SIEMPRE al menos una noticia sobre comerç "
                "de proximitat, eixos comercials urbans, comercio local, comercio de "
                "barrio, supermercat de proximitat, franquicia local o formatos de "
                "proximidad. Debe sustituir a la noticia de menor relevancia analítica "
                "del Bloque 2. Si no hay ninguna noticia de proximidad o eixos comercials "
                "en el snapshot, indícalo en TRAZABILIDAD bajo el epígraf "
                "'Proximitat: no disponible — [motiu]'.\n"
                + rule_12
                + "13. Coherencia terminológica entre bloques: las 'empresas "
                "unilocalizadas' del ICM por modo de distribución y el 'petit "
                "comerç'/'pequeño comercio' son el MISMO grupo estadístico del INE, "
                "no categorías opuestas. Si el Bloque 3 muestra que las "
                "unilocalizadas crecen, el Bloque 1 no puede afirmar que el pequeño "
                "comercio se contrae sin matizar que se trata de la media: dentro de "
                "las unilocalizadas conviven establecimientos que crecen (los "
                "diferenciados) y establecimientos que contraen (los genéricos sin "
                "propuesta de valor). Nunca uses ambos términos como si fueran "
                "categorías opuestas o independientes.\n"
                + "ESTRUCTURA OBLIGATORIA DEL MARKDOWN (compose.py la parsea literalmente):\n\n"
                "A. Tres campos de cabecera, cada uno en su línea:\n"
                "   **Asunto:** <hasta 70 caracteres, un solo hilo conductor>\n"
                "   **Pre-header:** <una línea que complementa el asunto>\n"
                "   **Titular:** <4-7 palabras, tesis editorial afirmativa, "
                "ej. 'Dos Europas del retail.'> El Titular debe derivarse de la "
                "cifra protagonista del Bloque 1 y reflejar el mismo argumento: "
                "si la cifra es de ventas (CDMGE), el Titular habla de demanda o "
                "ritmo de ventas; si es de coste laboral, habla de costes o márgenes. "
                "No puede haber desconexión entre la cifra que el lector ve en el "
                "exhibit y la tesis que lee en el Titular.\n\n"
                + bloque1_instr
                + "C. Bloque 2: **◆ NUESTRA LECTURA** con los 3 titulares "
                "y su lectura editorial (sin estructura especial). Los tres deben "
                "provenir de medios distintos (regla 9). Al menos uno debe ser sobre "
                "proximitat o eixos comercials (regla 11).\n\n"
                + bloque3_instr + "\n\n"
                "E. Bloque 4: **◆ LA PREDICCIÓN** con la afirmación arriesgada "
                "firmada '*— J3B3*'.\n\n"
                "F. TRAZABILIDAD al final según regla 6. Incluir sempre l'epígraf "
                "'Proximitat' (disponible o no disponible amb motiu)."
            ),
        },
        {
            "type": "text",
            "text": f"<LINEA_EDITORIAL>\n{linea_editorial}\n</LINEA_EDITORIAL>",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"<ESTILO_EDITORIAL>\n{estil_editorial}\n</ESTILO_EDITORIAL>",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"<DICCIONARIO_DATOS>\n{diccionario}\n</DICCIONARIO_DATOS>",
            "cache_control": {"type": "ephemeral"},
        },
    ]

    historial_block = format_historial_para_prompt(historial_entries)

    parts = [
        f"Genera la edición Núm. {numero} de 'El Pulso de la semana' "
        f"para el envío del lunes {semana_str}.",
        "",
    ]

    # Mode P2: injectar el titular fixat al capdamunt
    if mode_editorial == "P2" and titular:
        parts.extend([
            f"**MODE P2 — TESI EDITORIAL MANA**\n\n"
            f"El Titular d'aquesta edició és FIXAT: \"{titular}\"\n"
            f"No el pots modificar sota cap circumstància. Tota la construcció "
            f"del Bloque 1 ha d'argumentar i evidenciar aquesta tesi. "
            f"Tria la dada del snapshot que millor la suporta.",
            "",
        ])

    if historial_block:
        parts.extend([historial_block, ""])
    parts.extend([
        "Datos disponibles para esta edición:",
        "",
        f"<META_SNAPSHOT>\n{meta}\n</META_SNAPSHOT>",
        "",
        f"<PULSO_DIARIO_CDMGE periodo=ultimos_60_dias>\n{cdmge_data}\n</PULSO_DIARIO_CDMGE>",
        "",
    ])

    # Datasets estructurals: injectar si existeixen al snapshot
    productivitat_path = semana_dir / "productivitat.csv"
    if productivitat_path.exists():
        prod_data = slice_productivitat(productivitat_path)
        parts.extend([
            f"<PRODUCTIVITAT_SECTOR>\n{prod_data}\n</PRODUCTIVITAT_SECTOR>",
            "",
        ])

    ocupacio_path = semana_dir / "ocupacio_comerc.csv"
    if ocupacio_path.exists():
        ocup_data = slice_ocupacio_spain(ocupacio_path)
        parts.extend([
            f"<OCUPACIO_SECTOR periodo=ultims_8_anys>\n{ocup_data}\n</OCUPACIO_SECTOR>",
            "",
        ])

    ipc_path = semana_dir / "ipc.csv"
    if ipc_path.exists():
        ipc_data = slice_ipc(ipc_path, mesos=24)
        parts.extend([
            f"<IPC_COMERC periodo=ultims_24_mesos>\n{ipc_data}\n</IPC_COMERC>",
            "",
        ])

    icm_path = semana_dir / "pulso_icm.csv"
    if icm_path.exists():
        icm_data = slice_icm(icm_path, mesos=15)
        parts.extend([
            f"<PULSO_ICM_INE periodo=ultims_15_mesos>\n{icm_data}\n</PULSO_ICM_INE>",
            "",
        ])
        if icm_ccaa_disponible(icm_path):
            icm_ccaa_data = slice_icm_ccaa(icm_path)
            parts.extend([
                f"<PULSO_ICM_CCAA>\n{icm_ccaa_data}\n</PULSO_ICM_CCAA>",
                "",
            ])

    icm_distribucio_path = semana_dir / "pulso_icm_distribucio.csv"
    if icm_distribucio_path.exists():
        icm_dist_data = slice_icm_distribucio(icm_distribucio_path, mesos=15)
        parts.extend([
            f"<PULSO_ICM_DISTRIBUCIO periodo=ultims_15_mesos>\n{icm_dist_data}\n</PULSO_ICM_DISTRIBUCIO>",
            "",
        ])

    # Marges per branca: només si el dataset està verificat (gate verificat=True).
    # La sèrie ve de l'INE (Encuesta Anual de Comercio, marge=EBE/vendes) i és
    # font primària verificada; si mai es marqués verificat=False, l'angle queda latent.
    marges_path = semana_dir / "marges_branca.csv"
    if marges_disponible and marges_path.exists():
        marges_data = slice_marges(marges_path)
        parts.extend([
            f"<MARGES_BRANCA font=INE periodicidad=anual>\n{marges_data}\n</MARGES_BRANCA>",
            "",
        ])

    if bloc3_mode == "cdmge_tasa_anual":
        mes_clau, cdmge_clau = slice_cdmge_dias_clave(semana_dir / "pulso_diario.csv")
        parts.extend([
            f"<PULSO_CDMGE_DIAS_CLAVE mes={mes_clau}>\n{cdmge_clau}\n</PULSO_CDMGE_DIAS_CLAVE>",
            "",
        ])
    elif bloc3_mode == "europeu":
        europa_data = slice_europa(semana_dir / "pulso_europeo.csv", meses=24)
        parts.extend([
            f"<PULSO_EUROPEO_EUROSTAT periodo=ultimos_24_meses>\n{europa_data}\n</PULSO_EUROPEO_EUROSTAT>",
            "",
        ])

    # AVISO_FRESCOR: only P1 (en P2, la frescor no mana)
    if mode_editorial == "P1" and periodo_actual:
        lag = eurostat_lag_setmanes(periodo_actual, semana_str)
        if lag > 7:
            parts.extend([
                f"<AVISO_FRESCOR_DADES>\n"
                f"El darrer periode Eurostat disponible és {periodo_actual}, "
                f"que té {lag} setmanes de retard respecte la data d'enviament ({semana_str}). "
                f"Aplica la regla 12: la cifra protagonista del Bloque 1 ha de procedir "
                f"del CDMGE (pulso_diario.csv), no de Eurostat.\n"
                f"</AVISO_FRESCOR_DADES>",
                "",
            ])

    if context_extra:
        parts.extend([
            f"<CONTEXT_MACRO>\n{context_extra}\n</CONTEXT_MACRO>",
            "",
        ])
    parts.extend([
        f"<RECOPILACION_PRENSA>\n{prensa}\n</RECOPILACION_PRENSA>",
        "",
        "Devuelve el borrador completo en Markdown, listo para revisión humana. "
        "Incluye al final la sección TRAZABILIDAD según la regla 6.",
    ])
    user_text = "\n".join(parts)
    messages = [{"role": "user", "content": user_text}]
    return system, messages


def main() -> int:
    args = parse_args()
    semana_str = args.semana
    semana_dir = ROOT / "data" / f"semana-{semana_str}"
    if not semana_dir.exists():
        print(f"Error: no existe snapshot para {semana_str}. "
              f"Ejecuta scripts/snapshot.py primero.", file=sys.stderr)
        return 1

    output_dir = ROOT / "output" / f"semana-{semana_str}"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_md = output_dir / "newsletter.md"
    if out_md.exists() and not args.force:
        print(f"Error: ya existe {out_md}. Usa --force para sobrescribir.", file=sys.stderr)
        return 1

    historial = [] if args.no_historial else load_historial()
    if historial:
        n_inject = min(len(historial), HISTORIAL_VENTANA)
        print(f"  Memoria editorial: {len(historial)} edición(es) previa(s); "
              f"inyecto las últimas {n_inject} al prompt")
    elif not args.no_historial:
        print("  Memoria editorial: vacía (primera edición o historial no encontrado)")

    linea, estil, diccionario = cargar_templates()

    # Llegir meta del snapshot per a la detecció de mode
    meta_path = semana_dir / "_meta.json"
    meta_dict = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    noticies_editor_meta = meta_dict.get("noticies_editor") or []

    # Detecció del mode editorial P1/P2
    if args.titular:
        mode_editorial = "P2"
        mode_motiu = f"titular fixat per l'editor: \"{args.titular}\""
    else:
        mode_editorial, mode_motiu = detectar_mode_editorial(historial, semana_str, meta_dict)

    print(f"  Mode editorial: {mode_editorial} ({mode_motiu})")

    # Tesi setmanal: es llegeix ja aquí (abans de decidir el Bloc 3) perquè
    # pot demanar explícitament una comparativa territorial (mode icm_ccaa).
    # No es consumeix/renombra fins després de generar (marcar_tesi_usada()),
    # així que llegir-la ara no interfereix amb el seu ús més avall.
    tesi_setmana = load_tesi_setmana()

    # Decisió del Bloque 3: cinc modes automàtics + tres manuals.
    periodo_actual = max_periodo_europeo(semana_dir / "pulso_europeo.csv")
    novedad = detectar_novetat_eurostat(periodo_actual, historial, semana_str)
    dies_mes = cdmge_dies_mes_actual(semana_dir / "pulso_diario.csv")

    # ICM per format de distribució: disponible si el snapshot l'ha capturat;
    # "novetat" si el periode no s'ha usat encara a cap edició prèvia (mateix
    # patró que l'Eurostat).
    icm_dist_disponible = (semana_dir / "pulso_icm_distribucio.csv").exists()
    periodo_icm_dist_actual = meta_dict.get("icm_distribucio", {}).get("ultimo_periodo", "") \
        if icm_dist_disponible else ""
    novetat_icm_dist = (
        detectar_novetat_icm_distribucio(periodo_icm_dist_actual, historial, semana_str)
        if icm_dist_disponible else False
    )

    # ICM per CCAA: disponible si pulso_icm.csv té desglossament territorial;
    # s'activa quan la tesi setmanal ho demana explícitament (regla d'intenció
    # editorial, no de novetat de dataset — ver tesi_demana_comparativa_territorial).
    icm_ccaa_ok = icm_ccaa_disponible(semana_dir / "pulso_icm.csv")
    demana_ccaa = tesi_demana_comparativa_territorial(tesi_setmana)
    if demana_ccaa and not icm_ccaa_ok:
        print("  Avís: la tesi setmanal demana comparativa territorial (CCAA) però "
              "pulso_icm.csv no té aquest desglossament; es recorre als criteris "
              "automàtics del Bloc 3.", file=sys.stderr)

    # Gate de marges: l'angle de marges per branca només és vàlid si el dataset
    # té verificat=True al snapshot (avui, sèrie oficial de l'INE).
    marges_meta_info = meta_dict.get("marges") or {}
    marges_verificat = bool(marges_meta_info.get("verificat"))

    if args.bloc3:
        bloc3_mode = args.bloc3
        if bloc3_mode == "marges_branca" and not marges_verificat:
            print("  Bloc 3: 'marges_branca' sol·licitat però el dataset de marges "
                  "NO està verificat (verificat=False) o no és al snapshot; "
                  "recau a context editorial", file=sys.stderr)
            bloc3_mode = "editorial_contexto"
        elif bloc3_mode == "icm_distribucio" and not icm_dist_disponible:
            print("  Bloc 3: 'icm_distribucio' sol·licitat però pulso_icm_distribucio.csv "
                  "no és al snapshot; recau a context editorial", file=sys.stderr)
            bloc3_mode = "editorial_contexto"
        elif bloc3_mode == "icm_ccaa" and not icm_ccaa_ok:
            print("  Bloc 3: 'icm_ccaa' sol·licitat però pulso_icm.csv no té "
                  "desglossament per CCAA; recau a context editorial", file=sys.stderr)
            bloc3_mode = "editorial_contexto"
        else:
            print(f"  Bloc 3: {bloc3_mode} (sobreescrit per --bloc3)")
    elif icm_ccaa_ok and demana_ccaa:
        bloc3_mode = "icm_ccaa"
        print("  Bloc 3: ICM per CCAA (la tesi setmanal demana comparativa territorial)")
    elif icm_dist_disponible and novetat_icm_dist:
        bloc3_mode = "icm_distribucio"
        print(f"  Bloc 3: ICM per format de distribució "
              f"({periodo_icm_dist_actual} és periode nou)")
    elif novedad:
        bloc3_mode = "europeu"
        print(f"  Bloc 3: gràfic europeu (Eurostat {periodo_actual} és periode nou)")
    elif dies_mes >= 10:
        bloc3_mode = "cdmge_tasa_anual"
        print(f"  Bloc 3: ritme CDMGE últims 30 dies "
              f"(Eurostat en {periodo_actual}, {dies_mes} dies al mes actual → ≥10)")
    else:
        bloc3_mode = "editorial_contexto"
        print(f"  Bloc 3: context editorial sense gràfic "
              f"(Eurostat en {periodo_actual}, {dies_mes} dies al mes actual → <10)")

    indicador_bloc3 = bloc3_mode

    # Detecció automàtica de fets macro a la premsa del snapshot. S'injecten
    # SEMPRE al prompt (via <CONTEXT_MACRO>) perquè Sonnet els ponderi a la
    # cifra del Bloque 1 i a la predicció, tant si generate.py s'executa dins
    # el pipeline de schedule.py com si es crida directament. El context passat
    # amb --context-extra s'hi AFEGEIX (no el substitueix).
    noticias_macro = detectar_noticias_macro(semana_dir / "recopilacion_prensa.md")
    contexts = []
    if noticias_macro:
        contexts.append(construir_contexto_macro(noticias_macro))
        print(f"  Fets macro detectats a la premsa: {len(noticias_macro)} "
              f"→ injectats al prompt")
        for n in noticias_macro:
            print(f"    · {n['data']} — {n['titol']}")
    else:
        print("  Fets macro detectats a la premsa: cap")
    if tesi_setmana:
        contexts.append(tesi_setmana)
        print("  Tesi setmanal (config/tesi_setmana.md) afegida al prompt")
    if args.context_extra:
        contexts.append(args.context_extra)
        print("  Context addicional (--context-extra) afegit al prompt")
    context_efectiu = "\n\n".join(contexts)

    modelo = SETTINGS["modelo"]["modelo"]
    client = Anthropic()

    # Bucle de generació amb comprovació anti-repetició: si la cifra
    # protagonista del Bloque 1 repeteix dataset+periode respecte l'edició
    # anterior (es_dada_repetida), es reintenta amb una instrucció explícita
    # d'usar un dataset o periode diferent, fins a MAX_REINTENTOS_CIFRA_REPETIDA
    # vegades. Si args.no_historial, no hi ha historial amb què comparar i el
    # bucle s'executa una sola vegada (comportament idèntic al d'abans).
    entry_candidate = None
    intentos = 0
    while True:
        system, messages = construir_prompts(
            semana_dir, semana_str, args.numero, linea, estil, diccionario, historial,
            bloc3_mode=bloc3_mode,
            context_extra=context_efectiu,
            periodo_actual=periodo_actual,
            mode_editorial=mode_editorial,
            titular=args.titular,
            marges_disponible=marges_verificat,
            hi_ha_noticies_editor=bool(noticies_editor_meta),
        )

        etiqueta_intento = f", reintento {intentos}/{MAX_REINTENTOS_CIFRA_REPETIDA}" if intentos else ""
        print(f"Generando borrador con {modelo} (mode {mode_editorial}{etiqueta_intento})...")
        response = client.messages.create(
            model=modelo,
            max_tokens=SETTINGS["modelo"]["max_tokens"],
            temperature=SETTINGS["modelo"]["temperatura"],
            system=system,
            messages=messages,
        )

        borrador = "".join(block.text for block in response.content if block.type == "text")

        # Resol els enllaços de redirecció de Google News (news.google.com/rss/
        # articles/…) a la URL real de l'editor. Només afecta els 2-3 enllaços que el
        # model ha triat per al butlletí. Si falla (xarxa, format de Google canviat),
        # es manté l'enllaç original: el butlletí no es bloqueja per això.
        try:
            obs_path = os.environ.get("OBSERVATORI_PATH")
            if obs_path and obs_path not in sys.path:
                sys.path.insert(0, obs_path)
            from modules.press import resolve_links_in_text  # type: ignore

            borrador, n_resolts = resolve_links_in_text(borrador)
            if n_resolts:
                print(f"  Enllaços Google News resolts a l'editor original: {n_resolts}")
        except Exception as e:
            print(f"  Aviso: no se pudieron resolver los enlaces de Google News ({e}). "
                  f"Se mantienen los enlaces de redirección.", file=sys.stderr)

        if args.no_historial:
            break

        try:
            entry_candidate = extract_historial_entry(
                client, modelo, args.numero, semana_str, borrador
            )
        except Exception as e:
            print(f"  Aviso: no se pudo comprobar la repetición de la cifra protagonista "
                  f"({e}). Se mantiene el borrador sin ese chequeo.", file=sys.stderr)
            break

        repetida, motivo = es_dada_repetida(entry_candidate, historial, semana_str)
        if not repetida:
            break
        if intentos >= MAX_REINTENTOS_CIFRA_REPETIDA:
            print(f"  Aviso: {motivo}, pero se agotaron los reintentos "
                  f"({MAX_REINTENTOS_CIFRA_REPETIDA}). Se mantiene la cifra.", file=sys.stderr)
            break

        intentos += 1
        print(f"  Cifra protagonista repetida: {motivo}. "
              f"Reintentando ({intentos}/{MAX_REINTENTOS_CIFRA_REPETIDA}) "
              f"con instrucción explícita de cambiar de dataset o periodo...")
        contexts.append(
            "ATENCIÓN — LA CIFRA PROTAGONISTA GENERADA REPETÍA UN DATO YA USADO: "
            f"{motivo}. Para esta edición, elige en el Bloque 1 una cifra "
            "protagonista DIFERENTE: un dataset distinto del snapshot, o el "
            "mismo dataset con un periodo distinto (un mes más reciente si "
            "está disponible, o un desglose distinto —CCAA, rama, modo de "
            "distribución— en vez de la media nacional ya usada). No repitas "
            "el dataset ni el periodo de la edición anterior."
        )
        context_efectiu = "\n\n".join(contexts)

    out_md.write_text(borrador, encoding="utf-8")

    if tesi_setmana:
        marcar_tesi_usada()

    if noticies_editor_meta:
        registrar_noticies_editor_usades(noticies_editor_meta, borrador, semana_str)
        marcar_noticies_editor_usades()

    usage = response.usage
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    print(f"Borrador escrito en {out_md}")
    print(f"  Tokens entrada base: {usage.input_tokens}")
    print(f"  Tokens entrada cache_creation: {cache_creation}")
    print(f"  Tokens entrada cache_read:     {cache_read}")
    print(f"  Tokens salida: {usage.output_tokens}")
    print(f"  Stop reason:   {response.stop_reason}")

    # Copia auditable del snapshot
    origen_dir = output_dir / "dades_origen"
    origen_dir.mkdir(exist_ok=True)
    for fname in [
        "pulso_diario.csv", "pulso_europeo.csv", "recopilacion_prensa.md",
        "_meta.json", "productivitat.csv", "ocupacio_comerc.csv", "ipc.csv",
        "pulso_icm.csv", "marges_branca.csv",
    ]:
        src = semana_dir / fname
        if src.exists():
            shutil.copy2(src, origen_dir / fname)

    # Actualizar historial editorial
    if not args.no_historial:
        try:
            # Reaprofita l'extracció feta al bucle anti-repetició; si per algun
            # motiu no es va poder fer (excepció capturada allà), es reintenta
            # aquí una última vegada.
            entry = entry_candidate if entry_candidate is not None else extract_historial_entry(
                client, modelo, args.numero, semana_str, borrador
            )
            entry["periodo_eurostat"] = periodo_actual
            entry["periodo_icm"] = meta_dict.get("icm", {}).get("ultimo_periodo", "")
            entry["periodo_icm_distribucio"] = periodo_icm_dist_actual
            entry["indicador_bloc3"] = indicador_bloc3
            entry["mode_editorial"] = mode_editorial
            if args.titular:
                entry["titular_fixat"] = args.titular
            # Guardar max anys per a la detecció P1/P2 de la propera edició
            entry["productivitat_any"] = meta_dict.get("productivitat", {}).get("ultimo_any")
            entry["ocupacio_any"] = meta_dict.get("ocupacio", {}).get("ultimo_any")
            # Evita duplicar la mateixa edició (numero, semana) en --force
            historial = [e for e in historial
                         if not (e.get("numero") == args.numero and e.get("semana") == semana_str)]
            historial.append(entry)
            save_historial(historial)
            print(f"  Historial editorial actualizado con Núm. {args.numero} "
                  f"(mode={mode_editorial}, bloc3={indicador_bloc3}, "
                  f"periodo_eurostat={periodo_actual}; total: {len(historial)} edición(es))")
        except Exception as e:
            print(f"  Aviso: no se pudo actualizar el historial editorial ({e}). "
                  f"El borrador está correctamente escrito.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
