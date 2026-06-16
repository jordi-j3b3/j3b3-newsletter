"""
Genera el borrador en Markdown de la edición semanal con Sonnet 4.6.

Lee:
- templates/linea_editorial.md     (cacheable vía prompt cache)
- templates/data_dictionary.md     (cacheable vía prompt cache)
- data/semana-YYYY-MM-DD/*         (snapshot semanal, ya congelado)

Escribe:
- output/semana-YYYY-MM-DD/newsletter.md      borrador editable
- output/semana-YYYY-MM-DD/dades_origen/*     copia auditable del snapshot

Uso:
    python scripts/generate.py --semana 2026-05-19 --numero 1
    python scripts/generate.py --semana 2026-05-19 --numero 1 --force
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
    SETTINGS = yaml.safe_load(f)


HISTORIAL_PATH = ROOT / "config" / "historial_editorial.json"
HISTORIAL_VENTANA = 6  # ediciones recientes a inyectar en el prompt

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
    """Segunda llamada barata a Sonnet para extraer los 4 campos del historial.

    Devuelve un dict con numero, semana, cifra, angulo_bloc1, tema_prediccion,
    noticias[3]. Lanza excepción si el modelo no devuelve JSON parseable —
    el caller la captura y omite la actualización sin romper el pipeline.
    """
    prompt = (
        "Has generado esta edición de la newsletter 'El Pulso de la semana':\n\n"
        "<EDICION>\n" + borrador + "\n</EDICION>\n\n"
        "Extrae los siguientes campos y devuelve EXCLUSIVAMENTE un JSON válido "
        "(sin texto adicional, sin code fences):\n\n"
        "{\n"
        '  "cifra": "<la cifra protagonista del bloque 1, p.ej. +4,1%>",\n'
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
    # El modelo a veces añade code fences pese a la instrucción
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    data = json.loads(text)
    return {
        "numero": numero,
        "semana": semana,
        "cifra": str(data.get("cifra", "")),
        "angulo_bloc1": str(data.get("angulo_bloc1", "")),
        "tema_prediccion": str(data.get("tema_prediccion", "")),
        "noticias": list(data.get("noticias", [])),
    }


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
    return p.parse_args()


def cargar_templates() -> tuple[str, str]:
    linea = (ROOT / "templates" / "linea_editorial.md").read_text(encoding="utf-8")
    diccionario = (ROOT / "templates" / "data_dictionary.md").read_text(encoding="utf-8")
    return linea, diccionario


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
    """¿Eurostat ha publicado un periodo nuevo desde la última edición?

    Compara `periodo_actual` (max periode del pulso_europeo.csv del snapshot
    actual, formato YYYY-MM) con el campo `periodo_eurostat` de la última
    edición previa registrada en el historial. Se excluyen las entradas de la
    propia edición que se está (re)generando —identificadas por su `semana`—
    para que un --force no se compare consigo mismo.

    Devuelve True (hay novedad → bloque 3 = gráfico europeo) si el periodo
    actual es más reciente que el de la última edición previa, o si no hay
    edición previa (primera edición). Devuelve False (sin novedad → bloque 3 =
    ritmo CDMGE últimos 30 días) si el periodo coincide o es anterior.
    """
    previas = [e for e in historial if e.get("semana") != semana_actual]
    if not previas:
        return True
    ultimo = previas[-1].get("periodo_eurostat")
    if not ultimo:
        return True
    return periodo_actual > str(ultimo)


def slice_cdmge_dias_clave(csv_path: Path) -> tuple[str, str]:
    """tasa_anual en los días clave (14, 18, 22, 26, 30/último) del mes más reciente.

    Ventana de segunda quincena: evita el ruido de acumulación de los primeros
    días del mes (con pocos días acumulados la tasa anual es muy volátil) y
    muestra la aceleración real hacia el cierre. Devuelve (mes 'YYYY-MM',
    bloque CSV 'dia,tasa_anual'). Para cada día objetivo se toma el valor de
    ese día, o el del último día disponible anterior si ese día no existe (mes
    incompleto). Mantiene el orden cronológico y elimina duplicados."""
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


def cdmge_dies_mes_actual(csv_path: Path) -> int:
    """Nombre de dies disponibles (files úniques de tasa_anual) al mes més recent del CDMGE."""
    df = pd.read_csv(csv_path, parse_dates=["data"])
    ta = df[df["indicador"] == "tasa_anual"].sort_values("data")
    if ta.empty:
        return 0
    ult = ta["data"].max().to_period("M")
    return int((ta["data"].dt.to_period("M") == ult).sum())


def construir_prompts(
    semana_dir: Path,
    semana_str: str,
    numero: int,
    linea_editorial: str,
    diccionario: str,
    historial_entries: list,
    bloc3_mode: str = "europeu",
    context_extra: str = "",
) -> tuple[list[dict], list[dict]]:
    """Construye (system, messages) para la llamada al modelo.

    bloc3_mode: "europeu" (gràfic Eurostat), "cdmge_tasa_anual" (ritme
    intramensual CDMGE, Eurostat sense periode nou i ≥10 dies al mes actual),
    "editorial_contexto" (text editorial sense gràfic, <10 dies al mes actual
    i Eurostat sense periode nou).
    """

    cdmge_data = slice_cdmge(semana_dir / "pulso_diario.csv", dias=60)
    prensa = (semana_dir / "recopilacion_prensa.md").read_text(encoding="utf-8")
    meta = (semana_dir / "_meta.json").read_text(encoding="utf-8")

    # Instrucció del Bloque 3 (D): tres modes.
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
                "propio del Observatorio: cualquiera de los bloques de datos <PULSO_...> "
                "del mensaje (pulso_diario.csv, pulso_europeo.csv, o cualquier dataset que "
                "se añada en el futuro como VAB, ocupación, empresas o productividad). NUNCA "
                "puede proceder de <RECOPILACION_PRENSA>: un dato de prensa no es fuente "
                "primaria del Bloque 1, porque el lector debe poder verificar la cifra "
                "directamente en el Observatorio. La prensa se comenta en el Bloque 2, nunca "
                "es la cifra protagonista del Bloque 1.\n"
                "9. Las tres noticias del Bloque 2 deben proceder de medios DISTINTOS: no "
                "repitas dos titulares del mismo medio en la misma edición. Tres noticias "
                "del mismo diario sugieren sesgo de fuente y restan credibilidad a la "
                "lectura editorial. Si la recopilación de prensa solo trae noticias de uno "
                "o dos medios, elige las tres con mayor diversidad de fuente posible y "
                "adviértelo en la sección TRAZABILIDAD.\n"
                "10. Cuando la cifra protagonista del Bloque 1 procede de pulso_diario.csv "
                "(CDMGE, indicador del INE sobre grandes cadenas de distribución), incluye "
                "siempre en el Bloque 1: (a) la fecha exacta del dato más reciente, que "
                "encontrarás en <META_SNAPSHOT> bajo pulso_diario.ultima_fecha; y (b) la "
                "nota literal: 'Dato más reciente disponible a [fecha]. El indicador del "
                "INE sobre grandes cadenas se publica con un desfase habitual de 30 días.' "
                "Puede ir en el campo Fuente: o integrada en el cuerpo, pero no puede "
                "omitirse.\n\n"
                "ESTRUCTURA OBLIGATORIA DEL MARKDOWN (compose.py la parsea literalmente):\n\n"
                "A. Tres campos de cabecera, cada uno en su línea:\n"
                "   **Asunto:** <hasta 70 caracteres, un solo hilo conductor>\n"
                "   **Pre-header:** <una línea que complementa el asunto>\n"
                "   **Titular:** <4-7 palabras, tesis editorial afirmativa, "
                "ej. 'Dos Europas del retail.'>\n\n"
                "B. Bloque 1, estructura literal:\n\n"
                "   **◆ LA CIFRA DE LA SEMANA**\n\n"
                "   **Cifra:** <p.ej. +4,1%>\n"
                "   **Contexto:** <descripción breve, "
                "p.ej. Ventas minoristas España · marzo 2026>\n"
                "   **Fuente:** <descripción + fuente sin códigos, "
                "p.ej. Variación interanual · Eurostat>\n\n"
                "   La cifra protagonista procede de un dataset propio del Observatorio "
                "(ver regla absoluta 8), nunca de la recopilación de prensa.\n\n"
                "   <2-3 párrafos de lectura editorial con la conclusión firmada>\n\n"
                "C. Bloque 2: **◆ NUESTRA LECTURA** con los 3 titulares "
                "y su lectura editorial (sin estructura especial). Los tres deben "
                "provenir de medios distintos (regla absoluta 9).\n\n"
                + bloque3_instr + "\n\n"
                "E. Bloque 4: **◆ LA PREDICCIÓN** con la afirmación arriesgada "
                "firmada '*— J3B3*'.\n\n"
                "F. TRAZABILIDAD al final según regla 6."
            ),
        },
        {
            "type": "text",
            "text": f"<LINEA_EDITORIAL>\n{linea_editorial}\n</LINEA_EDITORIAL>",
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
    # "editorial_contexto": cap dataset addicional; el model treballa amb PULSO_DIARIO_CDMGE
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

    linea, diccionario = cargar_templates()

    # Decisió del Bloque 3: tres modes.
    # 1. Eurostat ha publicat periode nou → gràfic europeu.
    # 2. Eurostat sense novetat I ≥10 dies CDMGE al mes actual → ritme intramensual.
    # 3. Eurostat sense novetat I <10 dies CDMGE → context editorial sense gràfic
    #    (principi de mes: la tasa_anual acumulada de pocs dies és molt volàtil).
    periodo_actual = max_periodo_europeo(semana_dir / "pulso_europeo.csv")
    novedad = detectar_novetat_eurostat(periodo_actual, historial, semana_str)
    dies_mes = cdmge_dies_mes_actual(semana_dir / "pulso_diario.csv")

    if novedad:
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

    system, messages = construir_prompts(
        semana_dir, semana_str, args.numero, linea, diccionario, historial,
        bloc3_mode=bloc3_mode,
        context_extra=args.context_extra,
    )

    modelo = SETTINGS["modelo"]["modelo"]
    print(f"Generando borrador con {modelo}...")
    client = Anthropic()
    response = client.messages.create(
        model=modelo,
        max_tokens=SETTINGS["modelo"]["max_tokens"],
        temperature=SETTINGS["modelo"]["temperatura"],
        system=system,
        messages=messages,
    )

    borrador = "".join(block.text for block in response.content if block.type == "text")
    out_md.write_text(borrador, encoding="utf-8")

    usage = response.usage
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    print(f"Borrador escrito en {out_md}")
    print(f"  Tokens entrada base: {usage.input_tokens}")
    print(f"  Tokens entrada cache_creation: {cache_creation}")
    print(f"  Tokens entrada cache_read:     {cache_read}")
    print(f"  Tokens salida: {usage.output_tokens}")
    print(f"  Stop reason:   {response.stop_reason}")

    # Copia auditable del snapshot junto al borrador
    origen_dir = output_dir / "dades_origen"
    origen_dir.mkdir(exist_ok=True)
    for fname in ["pulso_diario.csv", "pulso_europeo.csv", "recopilacion_prensa.md", "_meta.json"]:
        src = semana_dir / fname
        if src.exists():
            shutil.copy2(src, origen_dir / fname)

    # Actualizar historial editorial — robusto: si falla, el pipeline sigue
    if not args.no_historial:
        try:
            entry = extract_historial_entry(
                client, modelo, args.numero, semana_str, borrador
            )
            entry["periodo_eurostat"] = periodo_actual
            entry["indicador_bloc3"] = indicador_bloc3
            # Evita duplicar la misma edición (numero, semana) al regenerar con --force
            historial = [e for e in historial
                         if not (e.get("numero") == args.numero and e.get("semana") == semana_str)]
            historial.append(entry)
            save_historial(historial)
            print(f"  Historial editorial actualizado con Núm. {args.numero} "
                  f"(bloc3={indicador_bloc3}, periodo_eurostat={periodo_actual}; "
                  f"total: {len(historial)} edición(es))")
        except Exception as e:
            print(f"  Aviso: no se pudo actualizar el historial editorial ({e}). "
                  f"El borrador está correctamente escrito.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
