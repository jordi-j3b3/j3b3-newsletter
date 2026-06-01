"""Mirall automàtic al dashboard, sense pas d'enviament.

Pensat per a cron / LaunchAgent: detecta la setmana més recent a `output/`
amb un `newsletter.md` generat i publica el contingut al repo del dashboard
(observatori-comerc). Idempotent: si ja s'ha publicat, mirror.py no fa res.

Per què existeix aquest script:
- `run_newsletter.py` és interactiu (norma absoluta: confirmació humana per
  enviar). No es pot programar a cron tal com està.
- Quan l'enviament es fa des del panel de Brevo (programat al web), el
  `send.py` no s'executa i `mirror_to_dashboard()` mai s'activa.
- Aquest script desacobla: l'enviament el fa Brevo, el mirall el fa el cron.

Ús manual:
    python scripts/mirror_only.py                # detecta setmana més recent
    python scripts/mirror_only.py --setmana 2026-06-01 --numero 3
    python scripts/mirror_only.py --dry-run      # només mostra què faria
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mirror import mirror_to_dashboard  # noqa: E402


def llistar_setmanes() -> list[str]:
    """Setmanes amb newsletter.md a output/, ordenades cronologicament."""
    out = ROOT / "output"
    if not out.is_dir():
        return []
    setmanes = []
    for d in out.iterdir():
        if not d.is_dir() or not d.name.startswith("semana-"):
            continue
        if (d / "newsletter.md").is_file():
            setmanes.append(d.name.removeprefix("semana-"))
    return sorted(setmanes)


def numero_per_setmana(setmana: str, setmanes_totes: list[str]) -> int:
    """Numero d'edicio = posicio (1-indexada) en la sequencia historica."""
    try:
        return setmanes_totes.index(setmana) + 1
    except ValueError:
        raise SystemExit(f"Setmana {setmana} no trobada a output/")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--setmana", help="YYYY-MM-DD; default: l'ultima a output/")
    p.add_argument("--numero", type=int, help="Numero d'edicio; default: deduit")
    p.add_argument("--dry-run", action="store_true",
                   help="Mostra que faria sense executar")
    args = p.parse_args()

    setmanes = llistar_setmanes()
    if not setmanes:
        print("[mirror_only] Cap setmana amb newsletter.md a output/. Res a fer.")
        return 0

    setmana = args.setmana or setmanes[-1]
    numero = args.numero or numero_per_setmana(setmana, setmanes)

    print(f"[mirror_only] Setmana: {setmana}  ·  Numero d'edicio: {numero}")
    if args.dry_run:
        print("[mirror_only] --dry-run: no s'executa el mirall.")
        return 0

    mirror_to_dashboard(setmana, numero)
    return 0


if __name__ == "__main__":
    sys.exit(main())
