"""Mirall de la newsletter al dashboard públic (observatori-comerc).

A cada enviament publica l'edició al dashboard, de manera que queda visible:
1. Copia el newsletter.md → `data/newsletter/semana-YYYY-MM-DD.md` (arxiu a L_Lecturas).
2. Reescriu `data/cache/tesi_vigent.json` amb el TITULAR de l'edició → la tesi
   vigent de la home queda vinculada a l'últim Pulso enviat.
Després fa commit + pull --rebase + push al repo del dashboard.

Salta sense abortar si el repo destí no existeix (l'enviament ja s'ha fet; el
mirall es pot arreglar a mà). Idempotent: si no hi ha canvis, no fa cap commit.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mirror_to_dashboard(semana: str, numero: int) -> None:
    # OBSERVATORI_PATH és el nom canònic que fan servir snapshot.py i el
    # workflow; mantenim OBSERVATORI_REPO_PATH com a àlies retrocompatible.
    obs_root = Path(os.environ.get("OBSERVATORI_REPO_PATH")
                    or os.environ.get("OBSERVATORI_PATH")
                    or (ROOT.parent / "observatori-comerc")).expanduser().resolve()
    src = ROOT / "output" / f"semana-{semana}" / "newsletter.md"

    if not obs_root.is_dir():
        print(f"\n[mirror] Repo destí no trobat a {obs_root}. Salto espejado.")
        return
    if not src.is_file():
        print(f"\n[mirror] Origen no trobat: {src}. Salto espejado.")
        return

    md = src.read_text(encoding="utf-8")

    # 1) Arxiu de l'edició (L_Lecturas)
    target_dir = obs_root / "data" / "newsletter"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"semana-{semana}.md"
    shutil.copy2(src, target)
    rel_paths = [target.relative_to(obs_root)]
    print(f"\n[mirror] Copiat a {obs_root.name}/{rel_paths[0]}")

    # 2) Tesi vigent de la home = titular de l'edició (vinculada a cada enviament)
    tesi_path = obs_root / "data" / "cache" / "tesi_vigent.json"
    m = re.search(r"(?m)^\*\*Titular:\*\*\s*(.+)$", md)
    if m and tesi_path.parent.is_dir():
        titular = m.group(1).strip()
        tesi_path.write_text(
            json.dumps({
                "titol": titular,
                "data_publicacio": semana,
                "autor": "Observatorio del Comercio · J3B3 Consulting",
                "enllac_pulso": None,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rel_paths.append(tesi_path.relative_to(obs_root))
        print(f'[mirror] Tesi vigent de la home actualitzada: "{titular}"')

    msg = f"feat: mirall Pulso núm. {numero} (setmana {semana}) + tesi vigent home"
    try:
        subprocess.run(["git", "add", *[str(p) for p in rel_paths]], cwd=obs_root, check=True)
        # Només commiteja+pusha si hi ha canvis realment staged (idempotent).
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=obs_root)
        if staged.returncode != 0:
            subprocess.run(["git", "commit", "-m", msg], cwd=obs_root, check=True)
            # Sincronitza amb el remot abans de pujar: l'Action diària de dades
            # pot haver fet commits, i un push directe seria rebutjat.
            subprocess.run(["git", "pull", "--rebase"], cwd=obs_root, check=True)
            subprocess.run(["git", "push"], cwd=obs_root, check=True)
            print("[mirror] Publicat al dashboard: commit + push OK.")
        else:
            print("[mirror] Sense canvis: ja estava publicat.")
    except subprocess.CalledProcessError as e:
        print(f"[mirror] Git ha fallat ({e}). Resol manualment:")
        print(f"   cd {obs_root} && git add data/ && git commit -m '{msg}' && git push")
