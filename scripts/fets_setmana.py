"""
Lista de hechos del motor del Observatorio para la sesión de cada edición.

Lee data/semana-YYYY-MM-DD/fets.csv (copiado por snapshot.py desde
observatori-comerc/data/cache/fets.csv) y lo compara con la semana anterior:

  - nuevos        fet_id que no estaba
  - cambiados     mismo fet_id, enunciado distinto (valor, fecha o lectura)
  - se mantienen  los de mayor relevancia que siguen igual
  - desaparecidos ya no se cumplen con los datos actuales

Referencia: el fets.csv del snapshot anterior si existe en local; si no (en CI,
donde data/ no se versiona), la versión de fets.csv en el historial de git del
Observatorio de siete días antes.

Escribe data/semana-YYYY-MM-DD/fets_setmana.md. Los enunciados vienen en
catalán del motor: son material de trabajo, no texto para la edición. Cada
cifra que pase al boletín se verifica contra el CSV de origen, como siempre.

Uso:
    python scripts/fets_setmana.py                     # próximo lunes
    python scripts/fets_setmana.py --semana 2026-10-19
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

FETS_OBSERVATORI = "data/cache/fets.csv"
# Reglas cuyos hechos se pueden convertir en una predicción con umbral y fecha.
REGLAS_PREDICCION = {"ratxa", "extrem", "inflexio", "divergencia"}
TOP_SE_MANTIENEN = 10


def _referencia_local(semana: str) -> tuple[pd.DataFrame, str] | None:
    previas = sorted(p for p in (ROOT / "data").glob("semana-*/fets.csv")
                     if p.parent.name[len("semana-"):] < semana
                     and len(p.parent.name) == len("semana-YYYY-MM-DD"))
    if not previas:
        return None
    return pd.read_csv(previas[-1]), f"snapshot {previas[-1].parent.name}"


def _referencia_git(semana: str, obs_path: Path) -> tuple[pd.DataFrame, str] | None:
    limite = (datetime.strptime(semana, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    def git(*args):
        return subprocess.run(["git", "-C", str(obs_path), *args],
                              capture_output=True, text=True)

    rev = git("rev-list", "-1", f"--before={limite} 00:00", "HEAD", "--", FETS_OBSERVATORI)
    commit = rev.stdout.strip()
    if rev.returncode != 0 or not commit:
        return None
    contingut = git("show", f"{commit}:{FETS_OBSERVATORI}")
    if contingut.returncode != 0:
        return None
    return (pd.read_csv(io.StringIO(contingut.stdout)),
            f"historial del Observatorio, commit {commit[:7]} (antes del {limite})")


def compara(actual: pd.DataFrame, previa: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
    actual = actual.sort_values(["rellevancia", "fet_id"], ascending=[False, True])
    if previa is None:
        return {"nuevos": actual, "cambiados": actual.iloc[0:0],
                "se_mantienen": actual.iloc[0:0], "desaparecidos": actual.iloc[0:0]}
    ant = previa.set_index("fet_id")["enunciat"]
    es_nou = ~actual["fet_id"].isin(ant.index)
    canviat = ~es_nou & (actual["enunciat"] != actual["fet_id"].map(ant))
    cambiados = actual[canviat].copy()
    cambiados["antes"] = cambiados["fet_id"].map(ant)
    return {
        "nuevos": actual[es_nou],
        "cambiados": cambiados,
        "se_mantienen": actual[~es_nou & ~canviat].head(TOP_SE_MANTIENEN),
        "desaparecidos": previa[~previa["fet_id"].isin(actual["fet_id"])]
                         .sort_values("rellevancia", ascending=False),
    }


def _linea(row) -> str:
    marcas = [row["regla"], f"rel. {row['rellevancia']:.1f}"]
    if isinstance(row.get("avis"), str):
        marcas.append(f"avisos: {row['avis'].replace(',', ', ')}")
    if row["regla"] in REGLAS_PREDICCION:
        marcas.append("candidata a predicción")
    return f"- {row['enunciat']}  \n  _{' · '.join(marcas)}_"


def informe(semana: str, actual: pd.DataFrame, grupos: dict[str, pd.DataFrame],
            origen_ref: str | None) -> str:
    total = len(actual)
    lineas = [f"# Hechos del motor · semana {semana}", ""]
    if origen_ref is None:
        lineas += ["Sin referencia anterior: todos los hechos aparecen como nuevos.", ""]
    else:
        lineas += [f"Comparado con: {origen_ref}.", ""]
    lineas += [f"{total} hechos · nuevos: {len(grupos['nuevos'])} · "
               f"cambiados: {len(grupos['cambiados'])} · "
               f"desaparecidos: {len(grupos['desaparecidos'])}", "",
               "Enunciados en catalán, tal como salen del motor. Cualquier cifra que pase "
               "al boletín se verifica contra el CSV de origen.", ""]

    secciones = [("Nuevos", "nuevos"), ("Cambiados", "cambiados"),
                 (f"Se mantienen (los {TOP_SE_MANTIENEN} más relevantes)", "se_mantienen"),
                 ("Desaparecidos", "desaparecidos")]
    for titulo, clave in secciones:
        df = grupos[clave]
        if df.empty:
            continue
        lineas += [f"## {titulo}" + ("" if clave == "se_mantienen" else f" ({len(df)})"), ""]
        for _, row in df.iterrows():
            lineas.append(_linea(row))
            if clave == "cambiados":
                lineas.append(f"  Antes: {row['antes']}")
        lineas.append("")

    avisos = {}
    for _, row in actual.iterrows():
        if isinstance(row["avis"], str):
            for codi, text in zip(row["avis"].split(","), row["avisos_text"].split(" | ")):
                avisos[codi] = text
    if avisos:
        lineas += ["## Avisos de calidad", ""]
        lineas += [f"- **{c}**: {t}" for c, t in sorted(avisos.items())]
        lineas.append("")
    return "\n".join(lineas)


def genera(semana: str, obs_path: Path | None = None) -> dict | None:
    """Escribe fets_setmana.md en el snapshot de la semana. None si no hay fets.csv."""
    semana_dir = ROOT / "data" / f"semana-{semana}"
    fets_csv = semana_dir / "fets.csv"
    if not fets_csv.exists():
        return None
    actual = pd.read_csv(fets_csv)
    ref = _referencia_local(semana)
    if ref is None and obs_path is not None:
        ref = _referencia_git(semana, obs_path)
    previa, origen_ref = ref if ref else (None, None)
    grupos = compara(actual, previa)
    (semana_dir / "fets_setmana.md").write_text(
        informe(semana, actual, grupos, origen_ref), encoding="utf-8")
    return {"total": len(actual), "referencia": origen_ref,
            **{k: len(v) for k, v in grupos.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--semana", help="Lunes de la edición, YYYY-MM-DD")
    args = parser.parse_args()
    if args.semana:
        semana = args.semana
    else:
        from snapshot import next_monday
        semana = next_monday().strftime("%Y-%m-%d")
    obs_raw = os.environ.get("OBSERVATORI_PATH")
    info = genera(semana, Path(obs_raw).expanduser() if obs_raw else None)
    if info is None:
        print(f"Error: no hay fets.csv en data/semana-{semana}/ (¿snapshot sin hechos?)",
              file=sys.stderr)
        return 1
    print(f"fets_setmana.md · {info['total']} hechos · {info['nuevos']} nuevos · "
          f"{info['cambiados']} cambiados · {info['desaparecidos']} desaparecidos · "
          f"referencia: {info['referencia'] or 'ninguna'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
