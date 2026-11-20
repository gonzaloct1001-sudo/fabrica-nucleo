#!/usr/bin/env python3
"""Borra las ramas de respaldo wip/ abandonadas (núcleo 0.13).

Uso (lo corre cada día el flujo `.github/workflows/fabrica-estado.yml`; también a mano, desde la raíz):
    python .fabrica/scripts/limpiar_wip.py              muestra qué borraría
    python .fabrica/scripts/limpiar_wip.py --aplicar    las borra

Una rama `wip/<rama>` se borra en dos casos:
- su PR se integró y el respaldo es anterior a la integración (lo de después es trabajo nuevo: se conserva);
- lleva más de 14 días sin cambios y su rama de origen, `<rama>`, ya no existe en GitHub (se abandonó).

Usa `gh api` (solo REST). Ante cualquier respuesta dudosa de GitHub, no borra nada.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote

API = "repos/{owner}/{repo}"
DIAS = 14


class SinRespuesta(Exception):
    """GitHub no respondió con certeza (red, límite de uso, error del servidor): no se borra nada."""


def correr(orden):
    """La salida de `gh`; None si GitHub respondió 404; SinRespuesta ante cualquier otro error."""
    try:
        hecho = subprocess.run(orden, capture_output=True, encoding="utf-8", errors="replace", timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SinRespuesta(str(error)) from error
    if hecho.returncode == 0:
        return hecho.stdout
    if "HTTP 404" in (hecho.stderr or ""):
        return None
    raise SinRespuesta((hecho.stderr or "").strip()[:200])


def api(ruta, ejecutar, metodo="GET"):
    salida = ejecutar(["gh", "api", "-X", metodo, f"{API}/{ruta}"])
    try:
        return json.loads(salida) if salida else None
    except ValueError:
        return None


def abandonadas(ejecutar=correr, ahora=None):
    """[(rama wip, días sin cambios, motivo)] de las que se pueden borrar."""
    ahora = ahora or datetime.now(timezone.utc)
    refs = api("git/matching-refs/heads/wip/", ejecutar) or []
    borrar = []
    for ref in refs if isinstance(refs, list) else []:
        nombre = str(ref.get("ref", ""))[len("refs/heads/"):]
        origen = nombre[len("wip/"):]
        commit = api(f"git/commits/{(ref.get('object') or {}).get('sha', '')}", ejecutar) or {}
        fecha = ((commit.get("committer") or {}).get("date") or "").replace("Z", "+00:00")
        try:
            cuando = datetime.fromisoformat(fecha)
            dias = (ahora - cuando).days
        except ValueError:
            continue
        prs = api(f"pulls?state=closed&head={{owner}}:{quote(origen, safe='')}&per_page=10", ejecutar) or []
        integrados = []
        for pr in prs if isinstance(prs, list) else []:
            try:
                integrados.append(datetime.fromisoformat(str(pr.get("merged_at") or "").replace("Z", "+00:00")))
            except ValueError:
                continue
        if integrados and cuando <= max(integrados):
            borrar.append((nombre, dias, "su PR se integró"))
            continue
        if dias <= DIAS:
            continue
        if ejecutar(["gh", "api", f"{API}/git/ref/heads/{quote(origen, safe='/')}"]) is not None:
            continue  # la rama de origen sigue viva: su respaldo también (un error de GitHub corta antes)
        borrar.append((nombre, dias, f"{dias} días sin cambios y sin su rama de origen"))
    return borrar


def main(argumentos=None, ejecutar=correr):
    analizador = argparse.ArgumentParser(description="Borra las ramas wip/ abandonadas.")
    analizador.add_argument("--aplicar", action="store_true", help="las borra (sin esto, solo las muestra)")
    opciones = analizador.parse_args(argumentos)
    try:
        borrar = abandonadas(ejecutar)
    except SinRespuesta as error:
        print(f"GitHub no respondió con certeza ({error}): no se borra nada esta vez.")
        return 0
    if not borrar:
        print("No hay ramas wip/ para borrar.")
        return 0
    for nombre, _, motivo in borrar:
        if opciones.aplicar:
            try:
                hecho = ejecutar(["gh", "api", "-X", "DELETE", f"{API}/git/refs/heads/{quote(nombre, safe='/')}"])
            except SinRespuesta:
                hecho = None
            print(f"{'Borrada' if hecho is not None else 'No se pudo borrar'}: {nombre} ({motivo})")
        else:
            print(f"Se borraría: {nombre} ({motivo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
