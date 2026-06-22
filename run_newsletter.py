"""
Orquestrador interactivo del pipeline 'El Pulso de la semana'.

Flujo (todos los pasos requieren la presencia humana):
1. Detección o pregunta de semana de envío.
2. Snapshot de datos del Observatorio (congelado).
3. Generación del borrador en Markdown con Sonnet 4.6.
4. Edición opcional en el editor por defecto.
5. Composición del HTML del email.
6. Envío de preview automático al grupo MAILERLITE_GROUP_PREVIEW_ID.
7. Confirmación explícita doble antes del envío al grupo destino.

Norma absoluta: en ningún momento se envía al grupo destino sin
confirmación explícita escrita en terminal.

Uso:
    python run_newsletter.py
    python run_newsletter.py --semana 2026-05-19 --numero 1
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "config" / ".env")

sys.path.insert(0, str(ROOT / "scripts"))
from snapshot import next_monday  # noqa: E402


def pregunta(texto: str, default: str = "") -> str:
    suf = f" [{default}]" if default else ""
    resp = input(f"{texto}{suf}: ").strip()
    return resp or default


def confirmar(texto: str, default_yes: bool = False) -> bool:
    suf = "(S/n)" if default_yes else "(s/N)"
    while True:
        resp = input(f"{texto} {suf}: ").strip().lower()
        if not resp:
            return default_yes
        if resp in ("s", "si", "sí"):
            return True
        if resp in ("n", "no"):
            return False
        print("Respuesta no reconocida.")


def ejecutar(*cmd: str) -> None:
    print(f"\n$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Paso fallido: {' '.join(cmd)}")


def abrir_editor(path: Path) -> None:
    editor = os.environ.get("EDITOR")
    if editor:
        subprocess.run([editor, str(path)], check=True)
    else:
        # macOS: abre en el editor por defecto (-W espera al cierre)
        subprocess.run(["open", "-W", str(path)], check=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--semana", help="Fecha del lunes (YYYY-MM-DD). Default: próximo lunes.")
    p.add_argument("--numero", type=int, help="Número de edición.")
    p.add_argument("--skip-snapshot", action="store_true", help="No regenerar snapshot")
    p.add_argument("--skip-preview", action="store_true",
                   help="No ejecutar preview.py automático — útil para validar el flujo sin enviar email.")
    p.add_argument("--skip-send", action="store_true",
                   help="Saltar el paso de decisión final sin preguntar — equivalente a responder 'n'. "
                        "Combinado con --skip-preview hace un dry-run completo.")
    p.add_argument("--skip-mirror", action="store_true",
                   help="No copiar la newsletter al repo del dashboard tras el envío real.")
    p.add_argument("--titular", default="",
                   help="Titular fix (mode P2). Si buit, es pregunta interactivament "
                        "o el sistema detecta el mode automàticament.")
    args = p.parse_args()

    semana = args.semana or next_monday().strftime("%Y-%m-%d")
    print(f"Semana objetivo (lunes de envío): {semana}")
    if not args.semana and not confirmar("¿Confirmar esta semana?", default_yes=True):
        semana = pregunta("Introduce semana (YYYY-MM-DD)", semana)

    numero = args.numero
    if numero is None:
        try:
            numero = int(pregunta("Número de edición", "1"))
        except ValueError:
            print("Número inválido", file=sys.stderr)
            return 2

    semana_dir = ROOT / "data" / f"semana-{semana}"
    output_dir = ROOT / "output" / f"semana-{semana}"

    # Paso 1: snapshot
    if not args.skip_snapshot:
        if semana_dir.exists():
            print(f"Snapshot ya existe en {semana_dir} (congelado).")
        else:
            ejecutar(sys.executable, "scripts/snapshot.py", "--semana", semana)
    elif not semana_dir.exists():
        print(f"Error: --skip-snapshot pero no existe {semana_dir}", file=sys.stderr)
        return 1

    # Paso 2: generación
    # Preguntar titular (mode P2) si no s'ha passat per flag
    titular = args.titular
    if not titular:
        titular = pregunta(
            "Titular fix de l'edició (Enter per mode automàtic — dades decideixen)",
            "",
        )

    generate_cmd = [
        sys.executable, "scripts/generate.py",
        "--semana", semana, "--numero", str(numero),
    ]
    if titular:
        generate_cmd += ["--titular", titular]

    out_md = output_dir / "newsletter.md"
    if out_md.exists():
        print(f"Borrador existente en {out_md}")
        if confirmar("¿Regenerar el borrador?", default_yes=False):
            ejecutar(*generate_cmd, "--force")
    else:
        ejecutar(*generate_cmd)

    # Paso 3: edición opcional
    print(f"\nBorrador en: {out_md}")
    if confirmar("¿Abrir el borrador para revisar/editar?", default_yes=True):
        abrir_editor(out_md)

    # Paso 4: composición HTML
    ejecutar(sys.executable, "scripts/compose.py", "--semana", semana,
             "--numero", str(numero))

    # Paso 5: preview automática
    if args.skip_preview:
        print("\n[--skip-preview] Saltando envío de preview automático.")
    else:
        ejecutar(sys.executable, "scripts/preview.py", "--semana", semana,
                 "--numero", str(numero))

    # Paso 6: decisión final
    if args.skip_send:
        print("\n[--skip-send] Saltando paso de decisión final. Sin envío al grupo destino.")
    else:
        while True:
            opcion = pregunta(
                "Próxima acción: [s] enviar al grupo destino · [p] reenviar preview · [n] salir sin envío",
                "n",
            ).lower()
            if opcion == "s":
                cmd = [sys.executable, "scripts/send.py", "--semana", semana,
                       "--numero", str(numero)]
                if args.skip_mirror:
                    cmd.append("--skip-mirror")  # send.py és l'únic punt de mirall
                ejecutar(*cmd)
                break
            if opcion == "p":
                ejecutar(sys.executable, "scripts/preview.py", "--semana", semana,
                         "--numero", str(numero))
                continue
            print("Saliendo sin envío al grupo destino.")
            break

    print("\nFlujo completado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
