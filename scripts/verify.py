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

Severitat de les afirmacions (revisat 2026-08-28, després del Núm. 17)
---------------------------------------------------------------------
El primer disseny bloquejava sempre que la sèrie desmentia l'afirmació. El
resultat va ser el pitjor possible: el diumenge 2026-08-23 el gate va suspendre
un borrador correcte amb cinc "errors" —tots falsos— i, com que bloqueja la
cadena, no hi va haver campanya ni ningú se'n va adonar fins onze dies després.
Cap lector va rebre res el dilluns 24.

Els cinc falsos positius venien tots de la mateixa arrel: la resolució de sèrie
només exigia que coincidís l'ENTITAT, així que "la brecha de empleo joven entre
España y la UE-27" es resolia contra "ventas minoristas de España" i s'hi
comptava una ratxa que no hi tenia cap sentit. D'aquí quatre regles:

  1. Cal coincidència d'ENTITAT **i** de MÈTRICA (Serie.temes fa el pont entre
     l'etiqueta tècnica del CSV i la llengua del butlletí). Sense mètrica no hi
     ha resolució: AVÍS de "no s'ha pogut resoldre", no ERROR.
  2. La resolució té confiança "alta" o "baixa". Amb confiança baixa, un
     desquadrament és AVÍS. Bloquejar per una resolució dubtosa costa edicions;
     deixar passar un error de tant en tant no.
  3. Les afirmacions del Bloc 2 no bloquegen mai: allà el subjecte és una
     notícia i la font és el mitjà, no les nostres sèries.
  4. Una ratxa "en negatiu" sobre una sèrie que no té cap valor negatiu (nivells,
     índexs, milers d'ocupats) no és comprovable: la frase parlava d'una
     tendència qualitativa ("lleva quince años sin atraer jóvenes"). AVÍS.
     I si la ratxa real és més llarga que la declarada, el text es queda curt:
     tampoc és una afirmació falsa.

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

    `temes` és el vocabulari de la sèrie EN LA LLENGUA DEL PRODUCTE: les
    etiquetes dels CSV són tècniques i en català ('ICM real var_anual',
    'ocupats_milers') mentre el butlletí parla de 'ventas reales interanuales' i
    de 'ocupados'. Sense aquest pont, exigir coincidència de mètrica a la
    resolució de sèrie deixaria fora els encerts (i el gate només mirava
    l'entitat, que és com una afirmació sobre ocupació jove acabava resolta
    contra la sèrie de vendes minoristes pel fet de compartir 'España').
    """
    clau: str
    entitat: str
    metrica: str
    unitat: str
    punts: dict = field(default_factory=dict)
    temes: set[str] = field(default_factory=set)

    @property
    def etiqueta(self) -> str:
        return f"{self.entitat} · {self.metrica}"

    def periodes(self) -> list[str]:
        return _ordena_periodes(self.punts)

    @property
    def vocabulari(self) -> set[str]:
        """Tokens amb què es pot referir el text a aquesta mètrica."""
        return _tokens(self.metrica) | self.temes

    @property
    def te_negatius(self) -> bool:
        return any(v < 0 for v in self.punts.values())


def _afegeix(series: dict, clau: str, entitat: str, metrica: str, unitat: str,
             punts: dict, temes: str = "") -> None:
    punts = {p: v for p, v in punts.items() if v is not None and pd.notna(v)}
    if punts:
        series[clau] = Serie(clau, entitat, metrica, unitat, punts,
                             temes=_tokens(temes))


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


# Vocabulari de producte per família de dades (veure Serie.temes). En castellà,
# perquè és la llengua del butlletí; sense accents ni tokens de menys de 3
# lletres, que _tokens() descarta.
_TEMES_VENDES = ("ventas ventes comercio minorista detallista facturacion "
                 "negocio negocios indice volumen consumo")
_TEMES_VARIACIO = "variacion interanual anual tasa crecimiento ritmo caida"
_TEMES_OCUPACIO = ("ocupacion empleo ocupados trabajadores plantilla personal "
                   "puestos afiliados")
_TEMES_PREUS = "precios inflacion ipc encarecimiento cesta coste"
_TEMES_CONFIANCA = "confianza expectativas consumidor sentimiento clima animo"
_TEMES_EDAT = ("edad edades tramo tramos franja generacion generacional relevo "
               "jovenes joven mayores envejecimiento estructura")
_TEMES_PES = "peso cuota porcentaje proporcion participacion distribucion share"


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
            es_ocupacio = "ocupa" in str(tipus)
            temes = (_TEMES_OCUPACIO if es_ocupacio else _TEMES_VENDES) + " " + (
                _TEMES_VARIACIO if "var" in str(ind) else "") + " " + str(branca)
            _afegeix(S, f"icm|{ambit}|{tipus}|{branca}|{ind}",
                     entitat=str(ambit) if ambit != "nacional" else "España",
                     metrica=f"ICM {tipus} {ind} · {branca}",
                     unitat="%" if "var" in str(ind) else "index", punts=punts,
                     temes=temes)

    # -- ICM per modo de distribució ----------------------------------------
    f = semana_dir / "pulso_icm_distribucio.csv"
    if f.exists():
        df = pd.read_csv(f)
        for (tipus, modo, ind), g in df.groupby(["tipus", "modo", "indicador"]):
            punts = {f"{int(r.any_):04d}-{int(r.mes):02d}": float(r.valor)
                     for r in g.rename(columns={"any": "any_"}).itertuples()}
            es_ocupacio = "ocupa" in str(tipus)
            temes = ((_TEMES_OCUPACIO if es_ocupacio else _TEMES_VENDES) + " " +
                     (_TEMES_VARIACIO if "var" in str(ind) else "") +
                     " formato formatos modo cadenas superficies unilocalizadas")
            _afegeix(S, f"icmdist|{tipus}|{modo}|{ind}", entitat=str(modo),
                     metrica=f"ICM {tipus} {ind} por modo de distribución",
                     unitat="%" if "var" in str(ind) else "index", punts=punts,
                     temes=temes)

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
            _afegeix(S, f"ipc|{grup}|index", str(grup), "IPC índice", "index",
                     nivells, temes=_TEMES_PREUS)
            _afegeix(S, f"ipc|{grup}|yoy", str(grup), "IPC variación interanual",
                     "%", _yoy(nivells),
                     temes=f"{_TEMES_PREUS} {_TEMES_VARIACIO}")
            mom = {}
            per = _ordena_periodes(nivells)
            for a, b in zip(per, per[1:]):
                if nivells[a]:
                    mom[b] = (nivells[b] / nivells[a] - 1) * 100
            _afegeix(S, f"ipc|{grup}|mom", str(grup), "IPC variación mensual", "%",
                     mom, temes=f"{_TEMES_PREUS} mensual mes")

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
                          for r in df.itertuples() if pd.notna(getattr(r, col))},
                         temes=_TEMES_CONFIANCA)
        if {"expectatives_financera", "expectatives_economica"} <= set(df.columns):
            _afegeix(S, "icc|bretxa", "consumidor español",
                     "brecha de expectativas (personal menos general)", "punts",
                     {str(r.periode): float(r.expectatives_financera)
                      - float(r.expectatives_economica) for r in df.itertuples()},
                     temes=f"{_TEMES_CONFIANCA} brecha diferencia")

    # -- EPA del comerç (total, sense desglossar per sexe) ------------------
    f = semana_dir / "epa_retail.csv"
    if f.exists():
        df = pd.read_csv(f)
        tot = df[df["sexe"].astype(str).str.lower().isin(["total", "ambos sexos"])]
        if tot.empty:
            tot = df
        for col, nom, tema_col in [
            ("ocupats_cnae47_milers", "ocupados en el comercio al por menor (CNAE 47), miles",
             _TEMES_OCUPACIO),
            ("aturats_seccio_g_milers", "parados del comercio (sección G), miles",
             "parados paro desempleo desempleados"),
            ("hores_setmana_seccio_g", "horas semanales efectivas (sección G)",
             "horas jornada trabajadas semanales"),
        ]:
            if col in tot.columns:
                punts = {str(r.periode): float(getattr(r, col))
                         for r in tot.itertuples() if pd.notna(getattr(r, col))}
                _afegeix(S, f"epa|{col}", "comercio al por menor", nom, "milers",
                         punts, temes=f"{tema_col} epa")
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
                         f"{nom} · variación interanual", "%", yo,
                         temes=f"{tema_col} epa {_TEMES_VARIACIO}")

    # -- Eurostat retail per país ------------------------------------------
    f = semana_dir / "pulso_europeo.csv"
    if f.exists():
        df = pd.read_csv(f)
        for pais, g in df.groupby("pais"):
            _afegeix(S, f"eu|{pais}|yoy", str(pais),
                     "ventas minoristas (volumen) interanual", "%",
                     {str(r.periode): float(r.yoy) for r in g.itertuples()
                      if pd.notna(r.yoy)},
                     temes=f"{_TEMES_VENDES} {_TEMES_VARIACIO} eurostat")
            _afegeix(S, f"eu|{pais}|index", str(pais),
                     "ventas minoristas (volumen) índice", "index",
                     {str(r.periode): float(r.index_volum) for r in g.itertuples()
                      if pd.notna(r.index_volum)},
                     temes=f"{_TEMES_VENDES} eurostat")

    # -- CDMGE diari --------------------------------------------------------
    f = semana_dir / "pulso_diario.csv"
    if f.exists():
        df = pd.read_csv(f)
        for ind, g in df.groupby("indicador"):
            _afegeix(S, f"cdmge|{ind}", "grandes cadenas (CDMGE)", str(ind), "%",
                     {str(r.data): float(r.valor) for r in g.itertuples()
                      if pd.notna(r.valor)},
                     temes=f"{_TEMES_VENDES} {_TEMES_VARIACIO} cdmge diario "
                           f"grandes cadenas")

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
                     col.replace("_", " "), "%", punts,
                     temes="productividad coste laboral salarios salarial margen "
                           "margenes excedente cuota horas personal")

    f = semana_dir / "marges_branca.csv"
    if f.exists():
        df = pd.read_csv(f)
        for branca, g in df.groupby("branca"):
            _afegeix(S, f"marge|{branca}", str(branca), "margen sobre ventas", "%",
                     {str(int(r.any_)): float(r.marge_vendes_pct)
                      for r in g.rename(columns={"any": "any_"}).itertuples()
                      if pd.notna(r.marge_vendes_pct)},
                     temes="margen margenes rentabilidad ventas rama ramas")

    # -- Demografia empresarial per país (Eurostat BSD) ---------------------
    f = semana_dir / "estructura_empreses.csv"
    if f.exists():
        df = pd.read_csv(f)
        _BSD = {
            "ENT_NR": ("número de empresas del comercio", "",
                       "empresas censo parque tejido establecimientos comercios"),
            "ENT_BRTHR_PC": ("tasa de natalidad empresarial, %", "%",
                             "natalidad nacimiento aperturas altas creacion nuevas"),
            "ENT_DTHR_PC": ("tasa de defunción empresarial, %", "%",
                            "defuncion mortalidad cierres bajas desaparicion"),
            "ENT_BRTHR_DTHR_PC": ("rotación empresarial (natalidad + defunción), %", "%",
                                  "rotacion churn renovacion"),
            "GRW_ENT_PC": ("variación neta del número de empresas, %", "%",
                           "variacion neta crecimiento perdida saldo censo parque"),
            "EMP_NR": ("personas ocupadas en el comercio", "",
                       f"{_TEMES_OCUPACIO}"),
            "SAL_NR": ("asalariados del comercio", "",
                       "asalariados empleados contratados plantilla"),
        }
        for (pais, ind), g in df.groupby(["pais", "indic_sbs"]):
            metrica, unitat, temes = _BSD.get(
                str(ind), (str(ind), "", "empresas comercio"))
            _afegeix(S, f"bsd|{pais}|{ind}", str(pais), metrica, unitat,
                     {str(int(r.any_)): float(r.valor)
                      for r in g.rename(columns={"any": "any_"}).itertuples()
                      if pd.notna(r.valor)},
                     temes=f"{temes} comercio minorista empresas eurostat")

    _afegeix_ocupacio_edat(S, semana_dir)
    return S


# Trams del CSV agrupats com els anomena el butlletí ('los menores de 25', 'los
# mayores de 50'). Sense aquests agregats, una frase corrent com «en 2018 los
# mayores de 50 sumaban 444.100 ocupados» surt òrfena tot i ser dues cel·les del
# snapshot sumades: era el forat que va bloquejar el Núm. 17.
_AGREGATS_EDAT = {
    "menores de 25 años": ["15-24"],
    "de 25 a 49 años": ["25-39", "40-49"],
    "de 50 a 64 años": ["50-59", "60-64"],
    "mayores de 50 años": ["50-59", "60-64", "65+"],
    "todas las edades": ["15-24", "25-39", "40-49", "50-59", "60-64", "65+"],
}


def _afegeix_ocupacio_edat(S: dict, semana_dir: Path) -> None:
    """Ocupats al comerç per tram d'edat (Eurostat LFS), amb els agregats i els
    pesos que el butlletí publica.

    El dataset arribava al snapshot i al prompt des del 2026-06-22, però mai a
    aquest índex: qualsevol xifra d'estructura d'edat quedava ORFE i, al Bloc 1,
    això és ERROR. Es carreguen tres nivells: el tram, l'agregat i el pes sobre
    el total — perquè la cifra protagonista d'aquesta família sempre és un pes
    ('8,5% de ocupados menores de 25') i la bretxa amb la UE-27 també.
    """
    f = semana_dir / "ocupacio_comerc.csv"
    if not f.exists():
        return
    df = pd.read_csv(f)
    if "sex" in df.columns:
        df = df[df["sex"].astype(str).str.upper() == "T"]
    _PAIS_ES = {"Espanya": "España", "UE-27": "UE-27"}
    base = f"{_TEMES_OCUPACIO} {_TEMES_EDAT} comercio minorista lfs eurostat"

    pesos: dict[str, dict[str, dict[str, float]]] = {}
    for pais, gp in df.groupby("pais"):
        nom_pais = _PAIS_ES.get(str(pais), str(pais))
        per_tram = {str(edat): {str(int(r.any)): float(r.ocupats_milers)
                                for r in g.itertuples() if pd.notna(r.ocupats_milers)}
                    for edat, g in gp.groupby("edat")}
        anys = sorted({a for p in per_tram.values() for a in p})
        totals = {a: sum(p.get(a, 0.0) for p in per_tram.values()) for a in anys}

        for edat, punts in per_tram.items():
            _afegeix(S, f"ocupedat|{pais}|{edat}", f"{nom_pais}, tramo {edat} años",
                     "ocupados en el comercio al por menor por tramo de edad, miles",
                     "milers", punts, temes=base)

        pesos[nom_pais] = {}
        for nom, trams in _AGREGATS_EDAT.items():
            agregat = {a: sum(per_tram[t][a] for t in trams if a in per_tram.get(t, {}))
                       for a in anys}
            agregat = {a: v for a, v in agregat.items() if v}
            if not agregat:
                continue
            if nom != "todas las edades":
                _afegeix(S, f"ocupedat|{pais}|{nom}", f"{nom_pais}, {nom}",
                         "ocupados en el comercio al por menor, miles", "milers",
                         agregat, temes=base)
            quota = {a: 100 * v / totals[a] for a, v in agregat.items() if totals.get(a)}
            _afegeix(S, f"ocupedatpes|{pais}|{nom}", f"{nom_pais}, {nom}",
                     "peso sobre el total de ocupados del comercio, %", "%",
                     quota, temes=f"{base} {_TEMES_PES}")
            pesos[nom_pais][nom] = quota

    # Bretxa de pes entre Espanya i la UE-27: és la xifra que encapçala aquesta
    # família d'edicions ('5,7 puntos menos de jóvenes que la media europea').
    if {"España", "UE-27"} <= set(pesos):
        for nom in _AGREGATS_EDAT:
            es, ue = pesos["España"].get(nom, {}), pesos["UE-27"].get(nom, {})
            bretxa = {a: ue[a] - es[a] for a in es if a in ue}
            _afegeix(S, f"ocupedatbretxa|{nom}", f"España frente a la UE-27, {nom}",
                     "brecha de peso sobre el empleo del comercio, puntos",
                     "punts", bretxa,
                     temes=f"{base} {_TEMES_PES} brecha diferencia europa")


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


def bloc_de_la_frase(frase: str, blocs: list[tuple[str, str]]) -> str:
    """Diu a quin bloc del borrador viu una frase extreta per l'LLM.

    Cal per no bloquejar mai per una afirmació del Bloc 2: allà el subjecte és
    una notícia ('Cataluña lidera las aperturas de Charter'), la font és el
    mitjà i no hi ha cap sèrie nostra que pugui confirmar-la ni desmentir-la.
    """
    def pla(s: str) -> str:
        return re.sub(r"\s+", " ", _norm(s)).strip()

    f = pla(frase)
    if not f:
        return ""
    plans = [(nom, pla(text)) for nom, text in blocs]
    paraules = f.split()
    for clau in (f, " ".join(paraules[:8]), " ".join(paraules[:5])):
        if len(clau) < 12:
            continue
        for nom, text in plans:
            if clau in text:
                return nom
    return ""


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
    """Sèries i periodes on aquest número apareix com a cel·la.

    Les sèries d'ocupació vénen en MILERS i el butlletí escriu les persones
    senceres ('172.200 ocupados' = 172,2 del CSV). Es prova també el valor
    dividit per mil, amb la tolerància dividida igual: si el text imprimeix
    unitats, ±0,5 persones són ±0,0005 milers, o sigui que no s'afluixa el gate.
    """
    tol = _TOL_PER_DECIMALS.get(num.decimals, 0.005)
    hits = []
    for s in series.values():
        escales = [(num.valor, tol)]
        if s.unitat == "milers" and abs(num.valor) >= 1000:
            escales.append((num.valor / 1000, tol / 1000))
        for p, v in s.punts.items():
            if any(abs(v - objectiu) <= t for objectiu, t in escales):
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

_LLINDAR_ENTITAT = 0.5
# Per sota d'aquest solapament de mètrica la sèrie no es considera candidata: la
# coincidència d'entitat sola no és resolució (és el que resolia 'bretxa
# d'ocupació jove a Espanya' contra 'ventas minoristas de España').
_LLINDAR_METRICA_MINIM = 0.25
# A partir d'aquí la resolució es dona per SEGURA i un desquadrament bloqueja.
_LLINDAR_METRICA_ALTA = 0.5


def resol_serie(entitat: str, metrica: str, valor: float | None,
                periode: str | None, series: dict[str, Serie],
                ) -> tuple[Serie | None, list[Serie], str]:
    """Troba la sèrie de l'entitat i mètrica citades.

    Retorna (millor_candidata, altres_sèries_on_el_valor_encaixa, confiança). La
    segona llista és el diagnòstic d'atribució: si el valor no és a la sèrie de
    l'entitat citada però sí a la d'una altra, es pot dir de qui era.

    La confiança és "alta" o "baixa" i decideix la severitat, no el resultat:
    amb resolució incerta un desquadrament és AVÍS. Bloquejar per una resolució
    dubtosa va costar l'edició del Núm. 17 sencera (cinc "errors", tots falsos),
    i un gate que crida en fals s'acaba desactivant — que és pitjor que deixar
    passar un error de tant en tant.
    """
    te, tm = _tokens(entitat), _tokens(metrica)
    millor, millor_punts, millor_confianca = None, 0.0, ""
    for s in series.values():
        se = _tokens(s.entitat)
        if not se or not te:
            continue
        coincidencia_ent = _solapament(te, se)
        if coincidencia_ent < _LLINDAR_ENTITAT:
            continue
        coincidencia_met = _solapament(tm, s.vocabulari)
        # El valor citat al periode citat confirma la sèrie per si sol: és
        # evidència més forta que qualsevol coincidència d'etiquetes.
        confirmat = (valor is not None and periode and periode in s.punts
                     and abs(s.punts[periode] - valor) <= 0.05)
        if not confirmat and coincidencia_met < _LLINDAR_METRICA_MINIM:
            continue
        punts = coincidencia_ent + coincidencia_met + (2 if confirmat else 0)
        confianca = ("alta" if confirmat or coincidencia_met >= _LLINDAR_METRICA_ALTA
                     else "baixa")
        if punts > millor_punts:
            millor, millor_punts, millor_confianca = s, punts, confianca

    altres = []
    if valor is not None:
        for s in series.values():
            if s is millor:
                continue
            for p, v in s.punts.items():
                if abs(v - valor) <= 0.05 and (not periode or p == periode):
                    altres.append(s)
                    break
    return millor, altres, millor_confianca


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
    serie, altres, confianca = resol_serie(
        af.get("entidad", ""), af.get("metrica", ""), valor,
        af.get("periodo_final"), series)
    if serie is None:
        return "AVIS", (f"no s'ha pogut resoldre cap sèrie per a "
                        f"'{af.get('entidad')}' / '{af.get('metrica')}'")
    n_declarada = af.get("n")
    if not isinstance(n_declarada, int):
        return "AVIS", f"ratxa sense nombre de periodes; sèrie resolta: {serie.etiqueta}"

    direccio_declarada = (af.get("direccion") or "").lower()
    if direccio_declarada in ("negativo", "negativa") and not serie.te_negatius:
        # Una sèrie de nivells (índexs, milers d'ocupats) no pot tenir cap ratxa
        # 'en negatiu'. Si hi hem arribat, la frase parlava d'una altra cosa
        # —sovint una tendència qualitativa, 'lleva quince años sin atraer
        # jóvenes'— i comptar-hi signes no verifica res.
        return "AVIS", (f"{serie.etiqueta}: la sèrie no té cap valor negatiu, o "
                        f"sigui que la ratxa 'en negatiu' no és comprovable aquí; "
                        f"afirmació qualitativa o sèrie mal resolta")

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
    if real > n_declarada:
        # El text es queda curt ('lleva más de una década' quan en són divuit).
        # No és una afirmació falsa: es reporta per si l'editor vol afinar-la.
        return "AVIS", msg + " · el text es queda curt, la ratxa real és més llarga"
    if confianca != "alta":
        return "AVIS", msg + (" · RESOLUCIÓ INCERTA (la mètrica citada no casa "
                              "clarament amb la sèrie): comprovació no bloquejant")
    return "ERROR", msg


def verifica_superlatiu(af: dict, series: dict[str, Serie]) -> tuple[str, str]:
    """'mínimo desde X' / 'primera vez desde X' / 'mínimo de la serie'."""
    valor = _num_es(str(af.get("valor"))) if af.get("valor") not in (None, "null") else None
    serie, altres, confianca = resol_serie(
        af.get("entidad", ""), af.get("metrica", ""), valor,
        af.get("periodo_final"), series)
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
    if confianca != "alta":
        return "AVIS", msg + (" · RESOLUCIÓ INCERTA (la mètrica citada no casa "
                              "clarament amb la sèrie): comprovació no bloquejant")
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
        blocs = parteix_blocs(cos)
        for af in afirmacions:
            tipus = (af.get("tipo") or "").lower()
            if tipus == "racha":
                nivell, detall = verifica_racha(af, series)
            else:
                nivell, detall = verifica_superlatiu(af, series)
            bloc = bloc_de_la_frase(af.get("frase") or "", blocs)
            if nivell == "ERROR" and bloc == "bloc2":
                nivell = "AVIS"
                detall += (" · Bloc 2 (notícies): la font és el mitjà i no les "
                           "nostres sèries — no bloqueja")
            etiqueta_bloc = f" [{bloc}]" if bloc else ""
            linia = (f"[{tipus}]{etiqueta_bloc} «{(af.get('frase') or '')[:110]}» "
                     f"→ {detall}")
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
