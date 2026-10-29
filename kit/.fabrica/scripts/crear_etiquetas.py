#!/usr/bin/env python3
"""Crea o actualiza en GitHub las etiquetas de la fábrica para este repositorio (.github/etiquetas.json).

Uso, desde la raíz del proyecto, con la CLI de GitHub (gh) autenticada:
    python .fabrica/scripts/crear_etiquetas.py [--simular]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true", help="mostrar los comandos sin ejecutarlos")
    a = ap.parse_args()
    etiquetas = json.loads((RAIZ / ".github" / "etiquetas.json").read_text(encoding="utf-8"))
    fallas = 0
    for e in etiquetas:
        cmd = ["gh", "label", "create", e["nombre"], "--color", e["color"], "--description", e["descripcion"], "--force"]
        if a.simular:
            print(" ".join(cmd))
            continue
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            fallas += 1
            print(f"No se pudo crear '{e['nombre']}': {(r.stderr or r.stdout).strip()[:200]}")
    if not a.simular:
        print(f"Etiquetas: {len(etiquetas) - fallas} de {len(etiquetas)} listas.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
