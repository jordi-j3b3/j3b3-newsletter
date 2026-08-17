"""
Regressió de scripts/verify.py sobre els incidents reals documentats al ROADMAP.

Cada cas és un borrador mínim que reprodueix un error que va arribar (o gairebé)
a publicar-se. El gate ha de suspendre'ls tots i ha de deixar passar el borrador
real del Núm. 16, que és correcte. Si algun dia un cas passa el gate, la
protecció s'ha trencat.

Ús (des de la còpia amb .venv i config/.env):
    .venv/bin/python tests/casos_verify/executa.py --semana 2026-08-17
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (fitxer, exit esperat, què ha de detectar)
CASOS = [
    ("cas1_atribucio_catalunya.md", 2,
     "atribueix a Catalunya la ratxa de sis mesos en negatiu que era de Balears "
     "(incident real del Núm. 15, 2026-08-10)"),
    ("cas2_ratxa_ipc_set_mesos.md", 2,
     "declara set mesos de desacceleració de l'IPC d'alimentació quan en són "
     "cinc: el gener puja al febrer (tesi del Núm. 16, detectat abans de publicar)"),
    (None, 0,
     "el borrador real del Núm. 16, que ha de passar el gate sense errors"),
]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semana", required=True)
    args = p.parse_args()

    fallades = 0
    for fitxer, esperat, descripcio in CASOS:
        cmd = [sys.executable, str(ROOT / "scripts" / "verify.py"),
               "--semana", args.semana]
        if fitxer:
            cmd += ["--fitxer", str(Path(__file__).parent / fitxer)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        ok = r.returncode == esperat
        fallades += not ok
        nom = fitxer or "borrador real"
        print(f"{'PASSA' if ok else 'FALLA'} · {nom} · exit {r.returncode} "
              f"(esperat {esperat})")
        print(f"        {descripcio}")
        if not ok:
            print("        --- sortida ---")
            for linia in (r.stderr or r.stdout).splitlines()[:12]:
                print(f"        {linia}")

    print(f"\n{len(CASOS) - fallades}/{len(CASOS)} casos correctes")
    return 1 if fallades else 0


if __name__ == "__main__":
    sys.exit(main())
