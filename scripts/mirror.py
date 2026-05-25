"""Mirall de la newsletter al dashboard públic (observatori-comerc).

Copia el newsletter.md de la setmana a `data/newsletter/semana-YYYY-MM-DD.md`
del repo del dashboard i fa commit + push. La pàgina L_Lecturas hi llegeix els
.md i mostra l'arxiu cronològic, així que cada enviament queda visible a la web.

Salta sense abortar si el repo destí no existeix (l'enviament ja s'ha fet; el
mirall es pot arreglar a mà). Idempotent: si el fitxer ja està publicat sense
canvis, no fa cap commit.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mirror_to_dashboard(semana: str, numero: int) -> None:
    obs_root = Path(os.environ.get("OBSERVATORI_REPO_PATH")
                    or (ROOT.parent / "observatori-comerc")).expanduser().resolve()
    src = ROOT / "output" / f"semana-{semana}" / "newsletter.md"

    if not obs_root.is_dir():
        print(f"\n[mirror] Repo destí no trobat a {obs_root}. Salto espejado.")
        return
    if not src.is_file():
        print(f"\n[mirror] Origen no trobat: {src}. Salto espejado.")
        return

    target_dir = obs_root / "data" / "newsletter"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"semana-{semana}.md"
    shutil.copy2(src, target)
    rel_target = target.relative_to(obs_root)
    print(f"\n[mirror] Copiat a {obs_root.name}/{rel_target}")

    msg = f"feat: mirall Pulso núm. {numero} (setmana {semana})"
    try:
        subprocess.run(["git", "add", str(rel_target)], cwd=obs_root, check=True)
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
        print(f"   cd {obs_root} && git add {rel_target} && "
              f"git commit -m '{msg}' && git push")
