#!/usr/bin/env python3
"""Hook de Claude Code: impide editar pruebas de aceptación aprobadas mientras se construye (núcleo 0.13, punto A7) y
crear «patas» en la zona del kit (núcleo 0.13.2).

Lo registra el kit en `.claude/settings.json` como hook `PreToolUse` de Edit, Write, MultiEdit y NotebookEdit. Busca
la marca en la copia de trabajo del archivo que se edita (la de la sesión o una hermana). Si existe
`.fabrica/trabajo/construyendo` (lo crean `construir` y `construir-en-sesion` al empezar y lo borran al
terminar) y el archivo que se quiere editar está en `pruebas/aceptacion/`, niega la edición y dice por qué. Quien
implementa nunca toca las pruebas aprobadas (constitución, art. II).

Además, siempre, niega que un agente edite un archivo que instaló el kit (los que lista
`.fabrica/nucleo-instalado.csv`) o cree uno nuevo dentro de la zona del kit (`NUCLEO.txt`) sin el prefijo `local-`:
una actualización lo pisaría. Los archivos propios que ya estaban en la zona se pueden seguir editando.

Solo niega: nunca aprueba ni reescribe nada, así que no se salta ningún permiso. Ante cualquier error, deja pasar
(la CI sigue protegiendo esas pruebas con la etiqueta `pruebas-aprobadas`).
"""
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

MARCA = Path(".fabrica/trabajo/construyendo")
PROTEGIDAS = "pruebas/aceptacion/"
MANIFIESTO = Path(".fabrica/nucleo-instalado.csv")


def negar(motivo):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": motivo}}


def instalados(copia):
    """Las rutas que instaló el kit en esta copia, o un conjunto vacío si no hay registro."""
    registro = copia / MANIFIESTO
    if not registro.is_file():
        return set()
    with open(registro, encoding="utf-8", newline="") as f:
        return {fila["ruta"] for fila in csv.DictReader(f) if fila.get("ruta")}


def zona_del_kit(copia):
    lista = copia / "NUCLEO.txt"
    if not lista.is_file():
        return ()
    return tuple(l.strip() for l in lista.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.lstrip().startswith("#"))


def pata_en_el_kit(copia, relativa, existe):
    """El motivo para negar la edición si es una «pata» en la zona del kit, o None."""
    kit = instalados(copia)
    if not kit:
        return None  # sin registro de lo instalado (el núcleo mismo, o un proyecto sin actualizar): no se sabe
    consejo = ("Lo propio va en un archivo local-* (por ejemplo .claude/skills/local-…), en docs/constitucion.md o en "
               "las rutas de .fabrica/proyecto.json; una mejora para todos se propone al núcleo (docs/aprendizajes.md). "
               "Si la Dirección igual quiere el cambio, lo hace ella a mano.")
    if relativa in kit:
        return (f"{relativa} es un archivo del kit de la fábrica: una actualización lo reemplazaría y el ajuste se "
                f"perdería. {consejo}")
    en_zona = any(relativa == e or (e.endswith("/") and relativa.startswith(e)) for e in zona_del_kit(copia))
    if en_zona and not existe and not any(parte.startswith("local-") for parte in relativa.split("/")):
        return (f"{relativa} sería un archivo nuevo dentro de la zona del kit sin el prefijo local-: se confundiría "
                f"con el kit. Usa un nombre local-*. {consejo}")
    return None


def copia_de(ruta, raiz):
    """La copia de trabajo de git que contiene `ruta` (puede ser una copia hermana de la sesión), o `raiz`."""
    carpeta = Path(ruta)
    while not carpeta.is_dir() and carpeta != carpeta.parent:
        carpeta = carpeta.parent
    try:
        hecho = subprocess.run(["git", "-C", str(carpeta), "rev-parse", "--show-toplevel"], capture_output=True,
                               encoding="utf-8", errors="replace", timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return raiz
    return Path(hecho.stdout.strip()) if hecho.returncode == 0 and hecho.stdout.strip() else raiz


def decidir(entrada, raiz):
    """La respuesta del hook para esta llamada, o None si se deja pasar."""
    datos = entrada.get("tool_input") or {}
    ruta = datos.get("file_path") or datos.get("notebook_path") or ""
    if not ruta:
        return None
    ruta = Path(ruta) if Path(ruta).is_absolute() else Path(raiz) / ruta
    copia = copia_de(ruta, Path(raiz))
    try:
        relativa = ruta.resolve().relative_to(copia.resolve()).as_posix()
    except (ValueError, OSError):
        return None
    motivo = pata_en_el_kit(copia, relativa, ruta.exists())
    if motivo:
        return negar(motivo)
    if not (copia / MARCA).exists() or not relativa.startswith(PROTEGIDAS):
        return None
    return negar(
        f"{relativa} es una prueba de aceptación aprobada y hay una construcción en curso "
        "(.fabrica/trabajo/construyendo). Quien implementa no la cambia: si hace falta, anótalo como duda para la "
        "Dirección y sigue; el cambio va en su propio PR de especificación. Si la construcción ya terminó y la "
        "marca quedó por error, bórrala.")


def main():
    try:
        entrada = json.loads(sys.stdin.read() or "{}")
        raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or entrada.get("cwd") or ".")
        respuesta = decidir(entrada, raiz)
    except Exception:  # noqa: BLE001 — un hook roto nunca debe detener el trabajo; la CI protege igual
        return 0
    if respuesta:
        print(json.dumps(respuesta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
