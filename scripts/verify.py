"""
Gate numèric del borrador: s'executa ENTRE generate.py i compose.py.

Per què existeix
----------------
El Núm. 15 (2026-08-10) va ser la primera edició amb un error FACTUAL i no
d'estil: el borrador afirmava que "Cataluña acumula seis meses consecutivos en
negativo en ventas reales". La ratxa de sis mesos era de **Balears**; Catalunya
va tancar el semestre en +1,2% acumulat. El model havia llegit bé una sèrie i
n'havia traslladat la propietat a la comunitat del costat. L'error va sobreviure
la generació i el va enxampar la revisió humana — que és precisament el que no
ha de ser l'única barrera.

El Núm. 16 (2026-08-17) va aportar el segon patró: una ratxa mal comptada. La
tesi parlava de "set mesos consecutius de desacceleració" de l'IPC
d'alimentació quan en són cinc (el gener puja al febrer, o sigui que la ratxa
arrenca al febrer). Aquesta vegada la va enxampar la verificació prèvia, però
el mecanisme era el mateix: una afirmació de ratxa que ningú comprovava contra
la sèrie.

Principi de disseny (el mateix que l'anti-al·lucinació de notícies de
snapshot.py): **el gate va a la capa de dades, no al prompt**. Una regla al
system prompt és defensa en profunditat, no la defensa principal. Aquí l'LLM
NOMÉS fa de parser —extreu afirmacions estructurades del text en prosa— i tota
la verificació es fa amb codi contra els CSV del snapshot. Si l'LLM s'inventa
una afirmació, la comprovació falla; si se'n salta una, cau al gate genèric de
números orfes.

Taxonomia dels números del cos (decidida 2026-08-16)
----------------------------------------------------
El ROADMAP advertia que un verificador massa estricte bloquejaria cada edició
per soroll i s'acabaria desactivant, que és el pitjor resultat possible. D'aquí
aquesta classificació, amb severitat diferent per categoria:

  ANCORAT   El número coincideix amb una cel·la d'una sèrie del snapshot
            (tolerància segons els decimals impresos). Correcte.
  DERIVAT   No és cel·la, però es reprodueix amb una operació simple entre dues
            cel·les ancorades (diferència, suma). Correcte.
  EXTERN    Apareix literalment al context efectiu de la generació
            (`context_efectiu.txt`: tesi de l'editor i fets macro de premsa).
            Correcte, però es llista: l'ha verificat l'editor, no aquest script.
  PREMSA    Apareix dins un paràgraf del Bloc 2 (notícies). Correcte amb avís:
            la font és el mitjà, no les nostres dades.
  ORFE      Cap de les anteriors. ERROR si és als blocs de dades propies
            (Bloc 1 i Bloc 3); AVÍS a la resta.

I les comprovacions que donen el valor real, perquè són falsables per
construcció sobre la sèrie:

  RATXA        "N meses consecutivos en negativo", "N trimestres seguidos"
  SUPERLATIU   "mínimo desde junio de 2021", "el más bajo de la serie"
  PRIMERA_VEZ  "primera caída desde el 3T 2022"

Codis de sortida
----------------
  0  cap error (pot haver-hi avisos)
  1  error d'ús / fitxers absents
  2  el borrador NO passa el gate: hi ha errors

Ús
--
    python scripts/verify.py --semana 2026-08-17
    python scripts/verify.py --semana 2026-08-17 --sense-llm   # només gate de números
    python scripts/verify.py --fitxer /ruta/borrador.md --semana 2026-08-17
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

# Tolerància relativa quan el número imprès té menys decimals que la sèrie.
# "3,2%" ha de casar amb 3,24 del CSV; "1,63%" no ha de casar amb 1,7.
_TOL_PER_DECIMALS = {0: 0.5, 1: 0.05, 2: 0.005, 3: 0.0005}

# Blocs del borrador. L'ordre importa: se parteix pel primer que apareix.
_BLOCS = [
    ("bloc1", r"◆\s*LA CIFRA DE LA SEMANA"),
    ("bloc2", r"◆\s*NUESTRA LECTURA"),
    ("bloc3", r"◆\s*DATOS DE LA SEMANA|◆\s*CONTEXTO DE LA SEMANA"),
    ("bloc4", r"◆\s*LA PREDICCIÓN"),
]
# Els blocs de dades pròpies: aquí un número orfe és ERROR, no avís.
_BLOCS_DADES_PROPIES = {"bloc1", "bloc3"}


# ---------------------------------------------------------------- utilitats

def _norm(s: str) -> str:
    """Minúscules sense accents ni signes, per comparar etiquetes i entitats."""
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^\w\s%]", " ", s)


def _tokens(s: str) -> set[str]:
    buides = {
        "de", "del", "la", "el", "los", "las", "en", "por", "para", "con", "y",
        "i", "al", "un", "una", "real", "reales", "the", "sin", "sobre",
    }
    return {t for t in _norm(s).split() if len(t) >= 3 and t not in buides}


def _casa_token(a: str, b: str) -> bool:
    """Dos tokens designen el mateix concepte?

    Cal tolerància perquè els CSV de l'Observatori porten les etiquetes en
    CATALÀ ('Alimentació i begudes no alcohòliques', 'Parament de la llar')
    mentre el butlletí és en castellà ('alimentación y bebidas', 'menaje del
    hogar'). Amb igualtat estricta la resolució de sèrie fallava i les
    afirmacions de ratxa sobre l'IPC quedaven sense verificar — silenciosament,
    que és el pitjor mode de fallada d'un gate.
    """
    if a == b:
        return True
    n = min(len(a), len(b))
    if n >= 5 and a[:n] == b[:n]:          # 'alimentacion' ~ 'alimentacio'
        return True
    # Semblança de caràcters, per als parells que no comparteixen prefix:
    # 'alcoholicas' ~ 'alcoholiques', 'ocupados' ~ 'ocupats'.
    return n >= 5 and SequenceMatcher(None, a, b).ratio() >= 0.82


def _solapament(a: set[str], b: set[str]) -> float:
    """Fracció de tokens del conjunt petit que troben parella al gran."""
    if not a or not b:
        return 0.0
    petit, gran = (a, b) if len(a) <= len(b) else (b, a)
    casats = sum(1 for t in petit if any(_casa_token(t, u) for u in gran))
    return casats / len(petit)


def _num_es(text: str) -> float | None:
    """Converteix un número escrit a l'espanyola ('1.234,5', '−0,4') a float."""
    t = text.strip().replace("−", "-").replace("–", "-").replace("−", "-")
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _decimals(text: str) -> int:
    return len(text.split(",")[1]) if "," in text else 0


def _ordena_periodes(punts: dict) -> list[str]:
    """Ordena periodes heterogenis: '2026-07' < '2026-T2' < '2026'.

    Es normalitza a una tupla (any, subperiode) on el subperiode d'un any sencer
    és 0 (va primer, perquè no competeix amb els mensuals de la mateixa sèrie).
    """
    def clau(p: str):
        m = re.match(r"^(\d{4})-T?(\d{1,2})$", p)
        if m:
            return (int(m.group(1)), int(m.group(2)))
        m = re.match(r"^(\d{4})$", p)
        if m:
            return (int(m.group(1)), 0)
        return (9999, 99)
    return sorted(punts, key=clau)


# ------------------------------------------------------------------- sèries

@dataclass
class Serie:
    """Una sèrie temporal del snapshot, amb el subjecte separat de la mètrica.

    `entitat` és el que permet detectar l'error d'atribució: si el text diu
    'Cataluña' i el valor només existeix a la sèrie de 'Illes Balears', la
    resolució per entitat falla i es pot dir exactament de qui era la dada.
    """
    clau: str
    entitat: str
    metrica: str
    unitat: str
    punts: dict = field(default_factory=dict)

    @property
    def etiqueta(self) -> str:
        return f"{self.entitat} · {self.metrica}"

    def periodes(self) -> list[str]:
        return _ordena_periodes(self.punts)


def _afegeix(series: dict, clau: str, entitat: str, metrica: str, unitat: str,
             punts: dict) -> None:
    punts = {p: v for p, v in punts.items() if v is not None and pd.notna(v)}
    if punts:
        series[clau] = Serie(clau, entitat, metrica, unitat, punts)


def _yoy(punts: dict, mesos: int = 12) -> dict:
    """Variació interanual derivada d'una sèrie d'índexs mensuals."""
    out = {}
    for p, v in punts.items():
        m = re.match(r"^(\d{4})-(\d{2})$", p)
        if not m or not v:
            continue
        anterior = f"{int(m.group(1)) - mesos // 12}-{m.group(2)}"
        if anterior in punts and punts[anterior]:
            out[p] = (v / punts[anterior] - 1) * 100
    return out


def carrega_series(semana_dir: Path) -> dict[str, Serie]:
    """Construeix l'índex de sèries verificables a partir del snapshot.

    Inclou sèries DERIVADES (variació interanual d'índexs, bretxa d'expectatives
    de l'ICC) perquè el butlletí publica sistemàticament aquests càlculs i no els
    nivells d'índex: sense derivar-les, tota xifra protagonista sortiria òrfena.
    """
    S: dict[str, Serie] = {}

    # -- ICM: (ambit, tipus, branca, indicador) -----------------------------
    f = semana_dir / "pulso_icm.csv"
    if f.exists():
        df = pd.read_csv(f)
        for (ambit, tipus, branca, ind), g in df.groupby(
                ["ambit", "tipus", "branca", "indicador"]):
            punts = {f"{int(r.any_):04d}-{int(r.mes):02d}": float(r.valor)
                     for r in g.rename(columns={"any": "any_"}).itertuples()}
            _afegeix(S, f"icm|{ambit}|{tipus}|{branca}|{ind}",
                     entitat=str(ambit) if ambit != "nacional" else "España",
                     metrica=f"ICM {tipus} {ind} · {branca}",
                     unitat="%" if "var" in str(ind) else "index", punts=punts)

    # -- ICM per modo de distribució ----------------------------------------
    f = semana_dir / "pulso_icm_distribucio.csv"
    if f.exists():
        df = pd.read_csv(f)
        for (tipus, modo, ind), g in df.groupby(["tipus", "modo", "indicador"]):
            punts = {f"{int(r.any_):04d}-{int(r.mes):02d}": float(r.valor)
                     for r in g.rename(columns={"any": "any_"}).itertuples()}
            _afegeix(S, f"icmdist|{tipus}|{modo}|{ind}", entitat=str(modo),
                     metrica=f"ICM {tipus} {ind} por modo de distribución",
                     unitat="%" if "var" in str(ind) else "index", punts=punts)

    # -- IPC per grups COICOP: nivells + interanual i mensual derivats ------
    # Les etiquetes del CSV vénen en CATALÀ i el butlletí és en castellà: es
    # tradueixen aquí, a l'arrel, en lloc de confiar-ho tot a la comparació
    # difusa de tokens.
    _GRUP_ES = {
        "Índex general": "índice general",
        "Alimentació i begudes no alcohòliques": "alimentación y bebidas no alcohólicas",
        "Vestit i calçat": "vestido y calzado",
        "Parament de la llar": "menaje del hogar",
    }
    f = semana_dir / "ipc_coicop.csv"
    if f.exists():
        df = pd.read_csv(f)
        df["grup"] = df["grup"].map(lambda g: _GRUP_ES.get(g, g))
        for grup, g in df.groupby("grup"):
            nivells = {str(r.periode): float(r.ipc) for r in g.itertuples()}
            _afegeix(S, f"ipc|{grup}|index", str(grup), "IPC índice", "index", nivells)
            _afegeix(S, f"ipc|{grup}|yoy", str(grup), "IPC variación interanual",
                     "%", _yoy(nivells))
            mom = {}
            per = _ordena_periodes(nivells)
            for a, b in zip(per, per[1:]):
                if nivells[a]:
                    mom[b] = (nivells[b] / nivells[a] - 1) * 100
            _afegeix(S, f"ipc|{grup}|mom", str(grup), "IPC variación mensual", "%", mom)

    # -- Confiança del consumidor: columnes + bretxa derivada --------------
    f = semana_dir / "confianza_consumidor.csv"
    if f.exists():
        df = pd.read_csv(f)
        for col, nom in [
            ("index_confianca", "índice de confianza del consumidor"),
            ("expectatives_financera", "expectativas financieras personales"),
            ("expectatives_economica", "expectativas económicas generales"),
            ("situacio_actual_financera", "situación financiera actual"),
            ("situacio_actual_economica", "situación económica actual"),
        ]:
            if col in df.columns:
                _afegeix(S, f"icc|{col}", "consumidor español", nom, "punts",
                         {str(r.periode): float(getattr(r, col))
                          for r in df.itertuples() if pd.notna(getattr(r, col))})
        if {"expectatives_financera", "expectatives_economica"} <= set(df.columns):
            _afegeix(S, "icc|bretxa", "consumidor español",
                     "brecha de expectativas (personal menos general)", "punts",
                     {str(r.periode): float(r.expectatives_financera)
                      - float(r.expectatives_economica) for r in df.itertuples()})

    # -- EPA del comerç (total, sense desglossar per sexe) ------------------
    f = semana_dir / "epa_retail.csv"
    if f.exists():
        df = pd.read_csv(f)
        tot = df[df["sexe"].astype(str).str.lower().isin(["total", "ambos sexos"])]
        if tot.empty:
            tot = df
        for col, nom in [
            ("ocupats_cnae47_milers", "ocupados en el comercio al por menor (CNAE 47), miles"),
            ("aturats_seccio_g_milers", "parados del comercio (sección G), miles"),
            ("hores_setmana_seccio_g", "horas semanales efectivas (sección G)"),
        ]:
            if col in tot.columns:
                punts = {str(r.periode): float(getattr(r, col))
                         for r in tot.itertuples() if pd.notna(getattr(r, col))}
                _afegeix(S, f"epa|{col}", "comercio al por menor", nom, "milers", punts)
                # Interanual trimestral derivat (T2 contra T2 de l'any anterior).
                yo = {}
                for p, v in punts.items():
                    m = re.match(r"^(\d{4})-T?(\d)$", p)
                    if not m:
                        continue
                    prev = f"{int(m.group(1)) - 1}-T{m.group(2)}"
                    prev_alt = f"{int(m.group(1)) - 1}-{m.group(2)}"
                    base = punts.get(prev, punts.get(prev_alt))
                    if base:
                        yo[p] = (v / base - 1) * 100
                _afegeix(S, f"epa|{col}|yoy", "comercio al por menor",
                         f"{nom} · variación interanual", "%", yo)

    # -- Eurostat retail per país ------------------------------------------
    f = semana_dir / "pulso_europeo.csv"
    if f.exists():
        df = pd.read_csv(f)
        for pais, g in df.groupby("pais"):
            _afegeix(S, f"eu|{pais}|yoy", str(pais),
                     "ventas minoristas (volumen) interanual", "%",
                     {str(r.periode): float(r.yoy) for r in g.itertuples()
                      if pd.notna(r.yoy)})
            _afegeix(S, f"eu|{pais}|index", str(pais),
                     "ventas minoristas (volumen) índice", "index",
                     {str(r.periode): float(r.index_volum) for r in g.itertuples()
                      if pd.notna(r.index_volum)})

    # -- CDMGE diari --------------------------------------------------------
    f = semana_dir / "pulso_diario.csv"
    if f.exists():
        df = pd.read_csv(f)
        for ind, g in df.groupby("indicador"):
            _afegeix(S, f"cdmge|{ind}", "grandes cadenas (CDMGE)", str(ind), "%",
                     {str(r.data): float(r.valor) for r in g.itertuples()
                      if pd.notna(r.valor)})

    # -- Productivitat i marges (anuals) -----------------------------------
    f = semana_dir / "productivitat.csv"
    if f.exists():
        df = pd.read_csv(f)
        for col in df.columns:
            if col == "any":
                continue
            punts = {str(int(r.any_)): float(getattr(r, col))
                     for r in df.rename(columns={"any": "any_"}).itertuples()
                     if pd.notna(getattr(r, col))}
            # quota_salarial i marge_brut vénen en tant per u; el butlletí els
            # publica en percentatge.
            if col in ("quota_salarial", "marge_brut"):
                punts = {p: v * 100 for p, v in punts.items()}
            _afegeix(S, f"prod|{col}", "comercio al por menor",
                     col.replace("_", " "), "%", punts)

    f = semana_dir / "marges_branca.csv"
    if f.exists():
        df = pd.read_csv(f)
        for branca, g in df.groupby("branca"):
            _afegeix(S, f"marge|{branca}", str(branca), "margen sobre ventas", "%",
                     {str(int(r.any_)): float(r.marge_vendes_pct)
                      for r in g.rename(columns={"any": "any_"}).itertuples()
                      if pd.notna(r.marge_vendes_pct)})

    return S


# --------------------------------------------------- extracció de números

@dataclass
class NumTrobat:
    text: str
    valor: float
    decimals: int
    unitat: str
    bloc: str
    context: str


_NUM_RE = re.compile(
    r"(?<![\w,.])(?P<signe>[-−–+]?)"
    r"(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)"
    r"\s*(?P<unitat>%|punto?s?\b|millones\b|mil millones\b|miles\b|euros?\b)?",
    re.IGNORECASE,
)


def parteix_blocs(cos: str) -> list[tuple[str, str]]:
    """Parteix el cos del borrador en (nom_bloc, text). El que va abans del
    Bloc 1 (assumpte, pre-header, titular) es tracta com a 'cabecera'."""
    marques = []
    for nom, patro in _BLOCS:
        m = re.search(patro, cos)
        if m:
            marques.append((m.start(), nom))
    marques.sort()
    if not marques:
        return [("cabecera", cos)]
    trossos = [("cabecera", cos[:marques[0][0]])]
    for i, (pos, nom) in enumerate(marques):
        fi = marques[i + 1][0] if i + 1 < len(marques) else len(cos)
        trossos.append((nom, cos[pos:fi]))
    return trossos


def _neteja_enllacos(text: str) -> str:
    """Treu URLs i destins de markdown. Els identificadors d'article d'un enllaç
    ('.../noticias/14007576/08/26/...') són números que no afirmen res i
    embrutarien el gate amb falsos orfes."""
    text = re.sub(r"\((?:https?://|/)[^)\s]*\)", "( )", text)
    return re.sub(r"https?://\S+", " ", text)


def extreu_numeros(cos: str) -> list[NumTrobat]:
    out = []
    for bloc, text in parteix_blocs(_neteja_enllacos(cos)):
        for m in _NUM_RE.finditer(text):
            brut = m.group("num")
            valor = _num_es(brut)
            if valor is None:
                continue
            signe = -1 if m.group("signe") in ("-", "−", "–") else 1
            unitat = (m.group("unitat") or "").lower().strip()
            # Els anys no són afirmacions numèriques: són marques temporals.
            if not unitat and "," not in brut and 1900 <= valor <= 2100:
                continue
            ini, fi = max(0, m.start() - 90), min(len(text), m.end() + 90)
            out.append(NumTrobat(
                text=m.group(0).strip(), valor=signe * valor,
                decimals=_decimals(brut), unitat=unitat, bloc=bloc,
                context=re.sub(r"\s+", " ", text[ini:fi]).strip()))
    return out


def ancora(num: NumTrobat, series: dict[str, Serie]) -> list[tuple[Serie, str]]:
    """Sèries i periodes on aquest número apareix com a cel·la."""
    tol = _TOL_PER_DECIMALS.get(num.decimals, 0.005)
    hits = []
    for s in series.values():
        for p, v in s.punts.items():
            if abs(v - num.valor) <= tol:
                hits.append((s, p))
    return hits


# ------------------------------------------- extracció d'afirmacions (LLM)

_PROMPT_CLAIMS = """Eres un extractor. Del texto siguiente, extrae TODAS las \
afirmaciones verificables de racha, superlativo o "primera vez". NO extraigas \
nada más: ni opiniones, ni predicciones, ni cifras sueltas sin afirmación de \
racha o superlativo.

Devuelve EXCLUSIVAMENTE un JSON válido, sin code fences:

{"afirmaciones": [
  {
    "frase": "<la frase literal del texto, completa>",
    "tipo": "<racha|superlativo|primera_vez>",
    "entidad": "<el SUJETO exacto al que el texto atribuye la propiedad, tal \
como aparece: 'Cataluña', 'Illes Balears', 'Pequeñas cadenas', 'alimentación y \
bebidas', 'ocupados CNAE 47', 'España'>",
    "metrica": "<qué se mide: 'ventas reales interanuales', 'IPC variación \
interanual', 'ocupados', 'margen sobre ventas'>",
    "periodo_final": "<periodo en el que termina la racha o al que se refiere \
el superlativo, formato YYYY-MM o YYYY-Tn o YYYY>",
    "valor": "<el valor citado en esa frase si lo hay, con coma decimal; si no \
hay, null>",
    "direccion": "<negativo|positivo|desaceleracion|aceleracion|caida|subida>",
    "n": <número de periodos de la racha, o null>,
    "referencia": "<para superlativo/primera_vez: desde cuándo. 'junio de \
2021', 'la serie', 'el año', '2022-T4'. Si no hay, null>"
  }
]}

Reglas:
- "direccion": 'negativo' = valores por debajo de cero. 'desaceleracion' = la \
serie baja pero puede seguir en positivo. 'caida' = el nivel baja.
- Si una frase encadena varias afirmaciones, devuelve una entrada por cada una.
- Si no hay ninguna afirmación de este tipo, devuelve {"afirmaciones": []}.

TEXTO:
"""


def extreu_afirmacions(cos: str, modelo: str) -> list[dict]:
    """Demana a l'LLM que faci NOMÉS de parser. La verificació és a la funció
    de sota, amb codi i contra els CSV: si aquí s'inventa res, allà falla."""
    from anthropic import Anthropic
    client = Anthropic()
    r = client.messages.create(
        model=modelo, max_tokens=2000, temperature=0.0,
        messages=[{"role": "user", "content": _PROMPT_CLAIMS + cos}],
    )
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text).get("afirmaciones", [])


# ------------------------------------------------------ resolució de sèrie

def resol_serie(entitat: str, metrica: str, valor: float | None,
                periode: str | None, series: dict[str, Serie],
                ) -> tuple[Serie | None, list[Serie]]:
    """Troba la sèrie de l'entitat i mètrica citades.

    Retorna (millor_candidata, altres_sèries_on_el_valor_encaixa). La segona
    llista és el diagnòstic d'atribució: si el valor no és a la sèrie de
    l'entitat citada però sí a la d'una altra, es pot dir de qui era.
    """
    te, tm = _tokens(entitat), _tokens(metrica)
    millor, millor_punts = None, 0.0
    for s in series.values():
        se, sm = _tokens(s.entitat), _tokens(s.metrica)
        if not se or not te:
            continue
        coincidencia_ent = _solapament(te, se)
        if coincidencia_ent < 0.5:
            continue
        coincidencia_met = _solapament(tm, sm)
        punts = coincidencia_ent + coincidencia_met
        # Bonus fort si el valor citat hi apareix al periode citat: és la
        # confirmació que hem resolt la sèrie correcta i no una germana.
        if valor is not None and periode and periode in s.punts:
            if abs(s.punts[periode] - valor) <= 0.05:
                punts += 2
        if punts > millor_punts:
            millor, millor_punts = s, punts

    altres = []
    if valor is not None:
        for s in series.values():
            if s is millor:
                continue
            for p, v in s.punts.items():
                if abs(v - valor) <= 0.05 and (not periode or p == periode):
                    altres.append(s)
                    break
    return millor, altres


# ----------------------------------------------------------- verificadors

def _compleix(v: float, direccio: str) -> bool:
    d = (direccio or "").lower()
    if d in ("negativo", "negativa"):
        return v < 0
    if d in ("positivo", "positiva"):
        return v > 0
    return True  # direccions de tendència es tracten a part


def verifica_racha(af: dict, series: dict[str, Serie]) -> tuple[str, str]:
    """Compta la ratxa real a la sèrie i la compara amb la declarada."""
    valor = _num_es(str(af.get("valor"))) if af.get("valor") not in (None, "null") else None
    serie, altres = resol_serie(af.get("entidad", ""), af.get("metrica", ""),
                                valor, af.get("periodo_final"), series)
    if serie is None:
        return "AVIS", (f"no s'ha pogut resoldre cap sèrie per a "
                        f"'{af.get('entidad')}' / '{af.get('metrica')}'")
    n_declarada = af.get("n")
    if not isinstance(n_declarada, int):
        return "AVIS", f"ratxa sense nombre de periodes; sèrie resolta: {serie.etiqueta}"

    per = serie.periodes()
    fi = af.get("periodo_final")
    if fi not in serie.punts:
        fi = per[-1]
    idx = per.index(fi)
    direccio = (af.get("direccion") or "").lower()

    real = 0
    if direccio in ("desaceleracion", "aceleracion", "caida", "subida"):
        # Ratxa de tendència: cada punt comparat amb l'anterior.
        puja = direccio in ("aceleracion", "subida")
        i = idx
        while i > 0:
            a, b = serie.punts[per[i - 1]], serie.punts[per[i]]
            if (b > a) if puja else (b < a):
                real += 1
                i -= 1
            else:
                break
    else:
        i = idx
        while i >= 0 and _compleix(serie.punts[per[i]], direccio):
            real += 1
            i -= 1

    if real == n_declarada:
        return "OK", (f"{serie.etiqueta}: ratxa de {real} periodes fins a {fi} "
                      f"— coincideix")
    detall = ", ".join(f"{p} {serie.punts[p]:+.2f}"
                       for p in per[max(0, idx - n_declarada - 1):idx + 1])
    msg = (f"{serie.etiqueta}: el text diu {n_declarada} periodes de "
           f"'{direccio}' fins a {fi}, la sèrie en dona {real}. Sèrie: {detall}")
    if altres:
        msg += (f" · ATRIBUCIÓ: el valor citat encaixa amb "
                f"{', '.join(s.etiqueta for s in altres[:3])}")
    return "ERROR", msg


def verifica_superlatiu(af: dict, series: dict[str, Serie]) -> tuple[str, str]:
    """'mínimo desde X' / 'primera vez desde X' / 'mínimo de la serie'."""
    valor = _num_es(str(af.get("valor"))) if af.get("valor") not in (None, "null") else None
    serie, altres = resol_serie(af.get("entidad", ""), af.get("metrica", ""),
                                valor, af.get("periodo_final"), series)
    if serie is None:
        return "AVIS", (f"no s'ha pogut resoldre cap sèrie per a "
                        f"'{af.get('entidad')}' / '{af.get('metrica')}'")
    per = serie.periodes()
    fi = af.get("periodo_final") if af.get("periodo_final") in serie.punts else per[-1]
    idx = per.index(fi)
    v_fi = serie.punts[fi]
    direccio = (af.get("direccion") or "").lower()
    busca_minim = direccio in ("negativo", "caida", "desaceleracion", "baixada")

    ref_text = af.get("referencia")
    ref = _periode_referencia(ref_text, per, fi)
    diu_serie_sencera = bool(ref_text) and "serie" in _norm(ref_text)
    if ref_text and not ref and not diu_serie_sencera:
        # El text ancora el superlatiu a un moment concret que no s'ha pogut
        # traduir a un periode de la sèrie. Comparar contra tota la sèrie donaria
        # errors falsos (i un verificador que crida en fals s'acaba desactivant,
        # que és el pitjor resultat). Es reporta com a avís per a revisió humana.
        return "AVIS", (f"{serie.etiqueta}: no s'ha pogut resoldre la referència "
                        f"temporal «{ref_text}»; superlatiu no verificat")
    # 'el más bajo DESDE junio de 2021' vol dir que el juny de 2021 va ser
    # l'última vegada que va ser més baix: el punt de referència queda FORA de
    # la finestra de comparació. Incloure'l feia saltar l'error contra la
    # mateixa dada que justifica l'afirmació.
    ini = per.index(ref) + 1 if ref in serie.punts else 0
    finestra = list(per[ini:idx])
    if busca_minim:
        violacions = [p for p in finestra if serie.punts[p] <= v_fi]
        rel = "més baix"
    else:
        violacions = [p for p in finestra if serie.punts[p] >= v_fi]
        rel = "més alt"

    abast = f"des de {ref}" if ref in serie.punts else "de tota la sèrie disponible"
    if not violacions:
        return "OK", f"{serie.etiqueta}: {v_fi:+.2f} a {fi} és el {rel} {abast}"
    msg = (f"{serie.etiqueta}: el text diu {rel} {abast}, però hi ha "
           f"{len(violacions)} periode(s) que ho superen "
           f"({', '.join(f'{p} {serie.punts[p]:+.2f}' for p in violacions[:4])})")
    if altres:
        msg += (f" · ATRIBUCIÓ: el valor citat encaixa amb "
                f"{', '.join(s.etiqueta for s in altres[:3])}")
    return "ERROR", msg


_ORDINALS_TRIMESTRE = {
    "primer": 1, "primero": 1, "1r": 1, "1er": 1,
    "segundo": 2, "2n": 2, "2o": 2,
    "tercer": 3, "tercero": 3, "3r": 3, "3er": 3,
    "cuarto": 4, "ultimo": 4, "4t": 4, "4o": 4,
}


def _periode_referencia(ref: str | None, periodes: list[str],
                        periode_final: str | None = None) -> str | None:
    """Tradueix 'junio de 2021', '2022-T4', 'el tercer trimestre de 2022' o 'el
    año' al periode de la sèrie que queda JUST ABANS de la finestra de
    comparació. Retorna None si no es pot resoldre; el caller distingeix 'no hi
    havia referència' de 'no s'ha pogut resoldre'."""
    if not ref:
        return None
    r = _norm(ref)
    if "serie" in r:
        return None
    # 'máximo del año' / 'el más alto del año': la finestra és l'any en curs, o
    # sigui que la referència és l'últim periode de l'any anterior.
    if re.search(r"\bano\b|\bany\b|ejercicio", r) and not re.search(r"\d{4}", r):
        if periode_final:
            m = re.match(r"^(\d{4})(?:-T?(\d{1,2}))?$", periode_final)
            if m:
                prev = int(m.group(1)) - 1
                for cand in (f"{prev}-12", f"{prev}-T4", str(prev)):
                    if cand in periodes:
                        return cand
        return None
    m = re.search(r"(\d{4})[- ]?t\s?(\d)", r)
    if m:
        cand = f"{m.group(1)}-T{m.group(2)}"
        return cand if cand in periodes else None
    # 'tercer trimestre de 2022' / 'cuarto trimestre de 2022'
    if "trimestre" in r:
        any_t = re.search(r"(\d{4})", r)
        for nom, n in _ORDINALS_TRIMESTRE.items():
            if re.search(rf"\b{nom}\b", r) and any_t:
                cand = f"{any_t.group(1)}-T{n}"
                return cand if cand in periodes else None
    mesos = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
             "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
             "octubre": 10, "noviembre": 11, "diciembre": 12}
    any_ = re.search(r"(\d{4})", r)
    for nom, n in mesos.items():
        if nom in r and any_:
            cand = f"{any_.group(1)}-{n:02d}"
            return cand if cand in periodes else None
    if any_ and any_.group(1) in periodes:
        return any_.group(1)
    return None


# ------------------------------------------------------------------ informe

def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", required=True, help="YYYY-MM-DD del dilluns")
    p.add_argument("--fitxer", help="Borrador a verificar (default: output/semana-X/newsletter.md)")
    p.add_argument("--sense-llm", action="store_true",
                   help="Només el gate de números; sense extracció d'afirmacions")
    p.add_argument("--json", dest="json_out", help="Desa l'informe en JSON en aquesta ruta")
    args = p.parse_args()

    semana_dir = ROOT / "data" / f"semana-{args.semana}"
    out_dir = ROOT / "output" / f"semana-{args.semana}"
    borrador = Path(args.fitxer) if args.fitxer else out_dir / "newsletter.md"
    if not borrador.exists():
        print(f"Error: no existeix el borrador {borrador}", file=sys.stderr)
        return 1
    if not semana_dir.exists():
        print(f"Error: no existeix el snapshot {semana_dir}", file=sys.stderr)
        return 1

    text = borrador.read_text(encoding="utf-8")
    cos = re.split(r"###\s*TRAZABILIDAD", text)[0]

    series = carrega_series(semana_dir)
    ctx_path = out_dir / "context_efectiu.txt"
    context = ctx_path.read_text(encoding="utf-8") if ctx_path.exists() else ""
    premsa = (semana_dir / "recopilacion_prensa.md")
    premsa_txt = premsa.read_text(encoding="utf-8") if premsa.exists() else ""

    print(f"verify.py · Núm. semana {args.semana}")
    print(f"  sèries carregades del snapshot: {len(series)}")
    if not context:
        print("  AVÍS: no hi ha context_efectiu.txt; les xifres de la tesi de "
              "l'editor sortiran com a òrfenes", file=sys.stderr)

    errors: list[str] = []
    avisos: list[str] = []
    classificacio = {"ANCORAT": 0, "DERIVAT": 0, "EXTERN": 0, "PREMSA": 0, "ORFE": 0}

    # ---- gate de números -------------------------------------------------
    nums = extreu_numeros(cos)
    orfes = []
    for n in nums:
        if ancora(n, series):
            classificacio["ANCORAT"] += 1
            continue
        if n.text.replace(" ", "") in context.replace(" ", "") or (
                re.search(re.escape(n.text.split()[0]), context) and n.text.split()[0] in context):
            classificacio["EXTERN"] += 1
            continue
        if n.bloc == "bloc2" and n.text.split()[0] in premsa_txt:
            classificacio["PREMSA"] += 1
            continue
        # Derivat: diferència o suma de dues cel·les ancorades qualssevol de
        # la mateixa sèrie (cobreix "la brecha es de X puntos", "son Y menos").
        if _es_derivat(n, series):
            classificacio["DERIVAT"] += 1
            continue
        classificacio["ORFE"] += 1
        orfes.append(n)

    for n in orfes:
        msg = f"[{n.bloc}] número sense ancoratge: «{n.text}» — context: …{n.context}…"
        (errors if n.bloc in _BLOCS_DADES_PROPIES else avisos).append(msg)

    # ---- afirmacions de ratxa i superlatiu -------------------------------
    if not args.sense_llm:
        modelo = os.environ.get("VERIFY_MODEL", "claude-sonnet-4-6")
        try:
            afirmacions = extreu_afirmacions(cos, modelo)
        except Exception as e:
            afirmacions = []
            avisos.append(f"no s'ha pogut extreure afirmacions ({e}); només "
                          f"s'ha aplicat el gate de números")
        print(f"  afirmacions de ratxa/superlatiu detectades: {len(afirmacions)}")
        for af in afirmacions:
            tipus = (af.get("tipo") or "").lower()
            if tipus == "racha":
                nivell, detall = verifica_racha(af, series)
            else:
                nivell, detall = verifica_superlatiu(af, series)
            linia = f"[{tipus}] «{(af.get('frase') or '')[:110]}» → {detall}"
            if nivell == "ERROR":
                errors.append(linia)
            elif nivell == "AVIS":
                avisos.append(linia)
            else:
                print(f"  OK · {detall}")

    # ---- informe ---------------------------------------------------------
    print("  números: " + " · ".join(f"{k} {v}" for k, v in classificacio.items()))
    if avisos:
        print(f"\n{len(avisos)} AVÍS(OS) — no bloquegen:")
        for a in avisos:
            print(f"  · {a}")
    if errors:
        print(f"\n{len(errors)} ERROR(S) — el borrador NO passa el gate:",
              file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"semana": args.semana, "errors": errors, "avisos": avisos,
             "classificacio": classificacio}, indent=2, ensure_ascii=False),
            encoding="utf-8")

    if errors:
        print("\nCorregeix el borrador i torna a passar verify.py abans de "
              "compose.py.", file=sys.stderr)
        return 2
    print("\nGate superat.")
    return 0


def _es_derivat(num: NumTrobat, series: dict[str, Serie]) -> bool:
    """El número es reprodueix com a diferència entre dos punts d'una mateixa
    sèrie, o entre dues sèries al mateix periode (bretxes i variacions)."""
    tol = _TOL_PER_DECIMALS.get(num.decimals, 0.005)
    objectiu = abs(num.valor)
    for s in series.values():
        vals = list(s.punts.values())
        if len(vals) > 400:            # sèries diàries: massa parells, s'omet
            continue
        for i, a in enumerate(vals):
            for b in vals[i + 1:]:
                if abs(abs(a - b) - objectiu) <= tol:
                    return True
    return False


if __name__ == "__main__":
    sys.exit(main())
