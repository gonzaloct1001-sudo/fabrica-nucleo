#!/usr/bin/env python3
"""Deja en GitHub las etiquetas de la fábrica para este repositorio (.github/etiquetas.json).

Crea las que faltan, actualiza el color y la descripción de las que ya existen, y quita las que GitHub crea por
defecto (bug, enhancement, etc.) para que el tablero use solo las de la fábrica. Usa la API REST mediante `gh api`, así
que funciona en local y en la nube.

Uso, desde la raíz del proyecto:
    python .fabrica/scripts/crear_etiquetas.py [--simular] [--conservar-predeterminadas] [--repo <dueño>/<nombre>]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parents[2]
PREDETERMINADAS = {"bug", "documentation", "duplicate", "enhancement", "good first issue", "help wanted", "invalid",
                   "question", "wontfix", "accessibility"}


def api(*args):
    r = subprocess.run(["gh", "api", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def repositorio(explicito):
    if explicito:
        return explicito
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=RAIZ, capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", (r.stdout or "").strip())
    if not m:
        sys.exit("No se pudo saber el repositorio: usa --repo <dueño>/<nombre>.")
    return m.group(1)


def main():
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true", help="mostrar lo que haría, sin cambiar nada")
    ap.add_argument("--conservar-predeterminadas", action="store_true", help="no quitar las etiquetas por defecto")
    ap.add_argument("--repo", help="<dueño>/<nombre>; por defecto, el del remoto origin")
    a = ap.parse_args()

    repo = repositorio(a.repo)
    deseadas = json.loads((RAIZ / ".github" / "etiquetas.json").read_text(encoding="utf-8"))
    rc, salida, error = api(f"repos/{repo}/labels", "--paginate", "--jq", ".[].name")
    if rc != 0:
        sys.exit(f"No se pudieron leer las etiquetas de {repo}: {error[:300]}")
    existentes = set(salida.splitlines())
    fallas = 0

    for e in deseadas:
        nombre = e["nombre"]
        if nombre in existentes:
            cmd = ["-X", "PATCH", f"repos/{repo}/labels/{quote(nombre, safe='')}"]
        else:
            cmd = ["-X", "POST", f"repos/{repo}/labels", "-f", f"name={nombre}"]
        cmd += ["-f", f"color={e['color']}", "-f", f"description={e['descripcion']}"]
        if a.simular:
            print(("Actualizar" if nombre in existentes else "Crear") + f": {nombre}")
            continue
        rc, _, error = api(*cmd)
        if rc != 0:
            fallas += 1
            print(f"No se pudo dejar '{nombre}': {error[:200]}")

    sobran = sorted((existentes & PREDETERMINADAS) - {e["nombre"] for e in deseadas})
    if not a.conservar_predeterminadas:
        for nombre in sobran:
            if a.simular:
                print(f"Quitar: {nombre}")
                continue
            rc, _, error = api("-X", "DELETE", f"repos/{repo}/labels/{quote(nombre, safe='')}")
            if rc != 0:
                fallas += 1
                print(f"No se pudo quitar '{nombre}': {error[:200]}")

    if not a.simular:
        quitadas = 0 if a.conservar_predeterminadas else len(sobran)
        print(f"Etiquetas en {repo}: {len(deseadas)} de la fábrica, {quitadas} predeterminadas quitadas, {fallas} fallas.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
