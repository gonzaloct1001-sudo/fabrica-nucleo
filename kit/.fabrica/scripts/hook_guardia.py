#!/usr/bin/env python3
"""Hook de Claude Code: impide editar pruebas de aceptación aprobadas mientras se construye (núcleo 0.13, punto A7).

Lo registra el kit en `.claude/settings.json` como hook `PreToolUse` de Edit, Write, MultiEdit y NotebookEdit. Si
existe `.fabrica/trabajo/construyendo` (lo crean `construir` y `construir-en-sesion` al empezar y lo borran al
terminar) y el archivo que se quiere editar está en `pruebas/aceptacion/`, niega la edición y dice por qué. Quien
implementa nunca toca las pruebas aprobadas (constitución, art. II).

Solo niega: nunca aprueba ni reescribe nada, así que no se salta ningún permiso. Ante cualquier error, deja pasar
(la CI sigue protegiendo esas pruebas con la etiqueta `pruebas-aprobadas`).
"""
import json
import os
import sys
from pathlib import Path

MARCA = Path(".fabrica/trabajo/construyendo")
PROTEGIDAS = "pruebas/aceptacion/"


def decidir(entrada, raiz):
    """La respuesta del hook para esta llamada, o None si se deja pasar."""
    if not (raiz / MARCA).exists():
        return None
    datos = entrada.get("tool_input") or {}
    ruta = datos.get("file_path") or datos.get("notebook_path") or ""
    if not ruta:
        return None
    try:
        relativa = Path(ruta).resolve().relative_to(raiz.resolve()).as_posix()
    except (ValueError, OSError):
        return None
    if not relativa.startswith(PROTEGIDAS):
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"{relativa} es una prueba de aceptación aprobada y hay una construcción en curso "
            "(.fabrica/trabajo/construyendo). Quien implementa no la cambia: si hace falta, anótalo como duda para la "
            "Dirección y sigue; el cambio va en su propio PR de especificación. Si la construcción ya terminó y la "
            "marca quedó por error, bórrala.")}}


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
