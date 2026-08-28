"""
Proves deterministes de la resolució de sèrie de scripts/verify.py.

Els casos `.md` passen el borrador sencer pel gate i, per tant, depenen d'una
crida a l'LLM que fa de parser: útil de punta a punta, però variable. Aquí
s'entren les afirmacions ja parsejades —tal com les va produir el parser el
2026-08-23— i es comprova la part que decideix la severitat, que és la que va
bloquejar el Núm. 17 amb cinc errors, tots falsos.

Ús (des de la còpia amb .venv):
    .venv/bin/python tests/casos_verify/unitaris.py --semana 2026-08-24
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import verify  # noqa: E402


def _claim(**kw) -> dict:
    base = {"frase": "", "tipo": "racha", "entidad": "", "metrica": "",
            "periodo_final": None, "valor": None, "direccion": "negativo",
            "n": None, "referencia": None}
    base.update(kw)
    return base


# Les tres afirmacions que el gate va marcar com a ERROR el 2026-08-23 sense
# ser-ho. Cap no és una ratxa comptable: dues són tendències qualitatives i la
# tercera és un fet de premsa.
FALSOS_POSITIUS = [
    (_claim(frase="Es un sector de plantilla madura, y lleva más de una década siéndolo.",
            entidad="el comercio minorista español",
            metrica="estructura de edad de la plantilla",
            periodo_final="2026-07", n=10),
     "tendència qualitativa d'estructura d'edat, resolta contra la confiança "
     "del consumidor pel fet de compartir 'español'"),
    (_claim(frase="La brecha de empleo joven entre España y la UE-27 en el comercio "
                  "minorista lleva al menos una década sin cerrarse",
            entidad="España", metrica="brecha de empleo joven",
            periodo_final="2026-06", n=10),
     "bretxa d'ocupació jove, resolta contra les vendes minoristes d'Espanya"),
    (_claim(frase="Cataluña lidera las aperturas de Charter (Consum) en el primer "
                  "semestre del año",
            tipo="superlativo", entidad="Cataluña", metrica="aperturas de tiendas",
            periodo_final="2026-06", direccion="positivo",
            referencia="el primer semestre"),
     "obertures de botigues d'una cadena: cap sèrie nostra no en parla"),
]

# I la que SÍ ha de bloquejar: l'incident real del Núm. 15.
VERTADER_POSITIU = _claim(
    frase="Cataluña acumula seis meses consecutivos en negativo en ventas reales",
    entidad="Cataluña", metrica="ventas reales interanuales",
    periodo_final="2026-06", n=6)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semana", required=True)
    args = p.parse_args()

    series = verify.carrega_series(ROOT / "data" / f"semana-{args.semana}")
    fallades = 0

    def comprova(condicio: bool, etiqueta: str, detall: str = "") -> None:
        nonlocal fallades
        fallades += not condicio
        print(f"{'PASSA' if condicio else 'FALLA'} · {etiqueta}")
        if detall:
            print(f"        {detall}")

    print(f"sèries carregades: {len(series)}\n")

    # 1-2. Llindar de mètrica i degradació a avís.
    for af, descripcio in FALSOS_POSITIUS:
        verifica = (verify.verifica_racha if af["tipo"] == "racha"
                    else verify.verifica_superlatiu)
        nivell, detall = verifica(af, series)
        comprova(nivell != "ERROR", f"no bloqueja: {descripcio}",
                 f"{nivell} · {detall[:150]}")

    # 3. El Bloc 2 no es verifica mai contra sèries pròpies.
    cos = (ROOT / "tests" / "casos_verify" / "cas3_falsos_positius.md").read_text(
        encoding="utf-8")
    blocs = verify.parteix_blocs(cos)
    bloc = verify.bloc_de_la_frase(FALSOS_POSITIUS[2][0]["frase"], blocs)
    comprova(bloc == "bloc2", "la frase de premsa es localitza al Bloc 2",
             f"bloc detectat: {bloc or '(cap)'}")

    # 4. La protecció que ja hi havia segueix dempeus.
    nivell, detall = verify.verifica_racha(VERTADER_POSITIU, series)
    comprova(nivell == "ERROR", "segueix bloquejant l'atribució falsa a Catalunya",
             f"{nivell} · {detall[:150]}")

    # 5. Forat de cobertura de l'ocupació per edat (Núm. 17): els números del
    #    cos han de tenir ancoratge, en milers i en persones.
    for text, valor, decimals in [("172.200", 172200, 0), ("150.000", 150000, 0),
                                  ("444.100", 444100, 0), ("624.700", 624700, 0),
                                  ("8,5", 8.5, 1), ("14,2", 14.2, 1)]:
        num = verify.NumTrobat(text=text, valor=valor, decimals=decimals,
                               unitat="", bloc="bloc1", context="")
        hits = verify.ancora(num, series)
        comprova(bool(hits), f"«{text}» té ancoratge al snapshot",
                 f"{len(hits)} coincidència(es); p.ex. "
                 f"{hits[0][0].etiqueta} a {hits[0][1]}" if hits else "cap")

    print(f"\n{'tot correcte' if not fallades else f'{fallades} comprovació(ns) falla'}")
    return 1 if fallades else 0


if __name__ == "__main__":
    sys.exit(main())
