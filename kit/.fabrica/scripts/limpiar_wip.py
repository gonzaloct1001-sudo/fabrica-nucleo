#!/usr/bin/env python3
"""Borra las ramas de respaldo wip/ abandonadas (núcleo 0.13).

Uso (lo corre cada semana el flujo `.github/workflows/fabrica-estado.yml`; también a mano, desde la raíz):
    python .fabrica/scripts/limpiar_wip.py              muestra qué borraría
    python .fabrica/scripts/limpiar_wip.py --aplicar    las borra

Una rama `wip/<rama>` se borra solo si cumple las dos condiciones:
- lleva más de 14 días sin cambios;
- su rama de origen, `<rama>`, ya no existe en GitHub (se integró y se borró, o se abandonó).

Las de un PR integrado las borra el mismo flujo al integrarse. Usa `gh api` (solo REST).
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

API = "repos/{owner}/{repo}"
DIAS = 14


def correr(orden):
    try:
        hecho = subprocess.run(orden, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return hecho.stdout if hecho.returncode == 0 else None


def api(ruta, ejecutar, metodo="GET"):
    salida = ejecutar(["gh", "api", "-X", metodo, f"{API}/{ruta}"])
    try:
        return json.loads(salida) if salida else None
    except ValueError:
        return None


def abandonadas(ejecutar=correr, ahora=None):
    """[(rama wip, días sin cambios)] de las que se pueden borrar."""
    ahora = ahora or datetime.now(timezone.utc)
    refs = api("git/matching-refs/heads/wip/", ejecutar) or []
    borrar = []
    for ref in refs if isinstance(refs, list) else []:
        nombre = str(ref.get("ref", ""))[len("refs/heads/"):]
        origen = nombre[len("wip/"):]
        commit = api(f"git/commits/{(ref.get('object') or {}).get('sha', '')}", ejecutar) or {}
        fecha = ((commit.get("committer") or {}).get("date") or "").replace("Z", "+00:00")
        try:
            dias = (ahora - datetime.fromisoformat(fecha)).days
        except ValueError:
            continue
        if dias <= DIAS:
            continue
        if ejecutar(["gh", "api", f"{API}/git/ref/heads/{origen}"]) is not None:
            continue  # la rama de origen sigue viva: su respaldo también
        borrar.append((nombre, dias))
    return borrar


def main(argumentos=None, ejecutar=correr):
    analizador = argparse.ArgumentParser(description="Borra las ramas wip/ abandonadas.")
    analizador.add_argument("--aplicar", action="store_true", help="las borra (sin esto, solo las muestra)")
    opciones = analizador.parse_args(argumentos)
    borrar = abandonadas(ejecutar)
    if not borrar:
        print("No hay ramas wip/ abandonadas.")
        return 0
    for nombre, dias in borrar:
        if opciones.aplicar:
            hecho = ejecutar(["gh", "api", "-X", "DELETE", f"{API}/git/refs/heads/{nombre}"])
            print(f"{'Borrada' if hecho is not None else 'No se pudo borrar'}: {nombre} ({dias} días sin cambios)")
        else:
            print(f"Se borraría: {nombre} ({dias} días sin cambios y sin su rama de origen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
