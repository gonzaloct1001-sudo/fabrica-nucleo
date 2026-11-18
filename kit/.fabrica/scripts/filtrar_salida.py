#!/usr/bin/env python3
"""Corre un comando y muestra solo lo que sirve de su salida, con el mismo código de salida (núcleo 0.13, A7).

Uso:  python .fabrica/scripts/filtrar_salida.py -- <comando y sus argumentos>
Ej.:  python .fabrica/scripts/filtrar_salida.py -- python -m pytest pruebas/pedidos -q

Una batería de pruebas que pasa entera escribe cientos de líneas que un agente lee sin provecho: cada línea son
tokens. Este script deja las fallas con su detalle, los errores, las advertencias de cobertura y el resumen final, y
recorta lo demás. Si la salida es corta (60 líneas o menos), la muestra completa. Nunca oculta el código de salida:
termina con el mismo que el comando, así que "pasa o falla" se lee igual que sin filtro.

Para ver todo, se corre el comando sin este script, o con FABRICA_SALIDA_COMPLETA=1.
"""
import os
import re
import subprocess
import sys

CORTA = 60
CONTEXTO = 40  # líneas que se muestran como máximo de cada bloque de falla
CLAVE = re.compile(r"(FAIL|ERROR|Error|Traceback|assert|AssertionError|WARNING|Warning|TOTAL|Required test coverage|"
                   r"\b\d+ (passed|failed|error|errors|skipped)\b|^=+ .* =+$|^-+ .* -+$|^E\s)")
INICIO_DE_BLOQUE = re.compile(r"^(_{3,} .* _{3,}|={3,} (FAILURES|ERRORS) ={3,}|Traceback)")


def filtrar(lineas):
    """Las líneas que importan, en orden. Muestra cada bloque de falla con hasta CONTEXTO líneas."""
    if len(lineas) <= CORTA:
        return lineas
    salida, en_bloque, omitidas = [], 0, 0
    for linea in lineas:
        if INICIO_DE_BLOQUE.search(linea):
            en_bloque = CONTEXTO
        if en_bloque > 0 or CLAVE.search(linea):
            if omitidas:
                salida.append(f"[... {omitidas} línea(s) sin fallas omitidas ...]")
                omitidas = 0
            salida.append(linea)
            en_bloque = max(0, en_bloque - 1)
        else:
            omitidas += 1
    if omitidas:
        salida.append(f"[... {omitidas} línea(s) sin fallas omitidas ...]")
        salida.extend(lineas[-2:])  # el final del comando, que suele traer su resumen
    return salida


def main(argumentos=None):
    argumentos = list(sys.argv[1:] if argumentos is None else argumentos)
    if argumentos[:1] == ["--"]:
        argumentos = argumentos[1:]
    if not argumentos:
        print(__doc__)
        return 2
    try:
        hecho = subprocess.run(argumentos, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
                               errors="replace", check=False)
    except OSError as error:
        print(f"No se pudo correr {argumentos[0]}: {error}")
        return 127
    lineas = hecho.stdout.splitlines()
    if os.environ.get("FABRICA_SALIDA_COMPLETA") != "1":
        lineas = filtrar(lineas)
    print("\n".join(lineas))
    print(f"[código de salida: {hecho.returncode}]")
    return hecho.returncode


if __name__ == "__main__":
    sys.exit(main())
