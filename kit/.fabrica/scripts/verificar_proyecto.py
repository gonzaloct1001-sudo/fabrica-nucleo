#!/usr/bin/env python3
"""Verifica un proyecto de la fábrica. Corre en la CI de cada proyecto y en local.

Uso:
    python .fabrica/scripts/verificar_proyecto.py                        revisa el kit y el estado del proyecto
    python .fabrica/scripts/verificar_proyecto.py --base origin/main     además, protege las pruebas de aceptación
    python .fabrica/scripts/verificar_proyecto.py --base main --etiquetas pruebas-aprobadas   (prueba local)

Comprueba que:
1. Existan las rutas de NUCLEO.txt y los archivos del proyecto (.fabrica/proyecto.json y .fabrica/estado.json).
2. proyecto.json y estado.json sean JSON válidos, con sus campos y los mismos identificadores.
3. Con --base: si los cambios desde la base tocan pruebas/aceptacion/, el PR tenga la etiqueta pruebas-aprobadas.
   Las etiquetas se leen del evento de GitHub (GITHUB_EVENT_PATH) o de --etiquetas.
4. Con --base: avisa, sin fallar, si el cambio supera las líneas útiles recomendadas.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ETIQUETA_PRUEBAS = "pruebas-aprobadas"
PRUEBAS_ACEPTACION = "pruebas/aceptacion/"
LINEAS_UTILES = 400
NO_CUENTAN = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock", "Cargo.lock", ".min.js")
FASES = {"descubrimiento", "especificacion", "construccion", "estabilizacion", "operacion", "cerrado"}
SEMAFOROS = {"verde", "amarillo", "rojo"}


def preparar_consola():
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def leer_json(rel, errores):
    p = RAIZ / rel
    if not p.exists():
        errores.append(f"Falta {rel}.")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        errores.append(f"{rel} no es un JSON válido: {ex}")
        return None


def revisar_kit(errores):
    lista = RAIZ / "NUCLEO.txt"
    if not lista.exists():
        errores.append("Falta NUCLEO.txt: este repositorio no tiene el kit de la fábrica.")
        return
    for linea in lista.read_text(encoding="utf-8").splitlines():
        e = linea.strip()
        if not e or e.startswith("#"):
            continue
        p = RAIZ / e
        if (e.endswith("/") and not p.is_dir()) or (not e.endswith("/") and not p.is_file()):
            errores.append(f"NUCLEO.txt lista {e}, pero no existe.")


def revisar_estado(errores):
    proyecto = leer_json(".fabrica/proyecto.json", errores)
    estado = leer_json(".fabrica/estado.json", errores)
    if proyecto is not None:
        for campo in ("cliente", "negocio", "proyecto"):
            if not proyecto.get(campo):
                errores.append(f".fabrica/proyecto.json no tiene '{campo}'.")
    if estado is not None:
        for campo in ("cliente", "negocio", "proyecto", "fase", "semaforo", "historias", "actualizado"):
            if campo not in estado:
                errores.append(f".fabrica/estado.json no tiene '{campo}'.")
        if estado.get("fase") and estado["fase"] not in FASES:
            errores.append(f".fabrica/estado.json: fase '{estado['fase']}' no es válida ({', '.join(sorted(FASES))}).")
        if estado.get("semaforo") and estado["semaforo"] not in SEMAFOROS:
            errores.append(f".fabrica/estado.json: semáforo '{estado['semaforo']}' no es válido.")
    if proyecto and estado:
        for campo in ("cliente", "negocio", "proyecto"):
            if proyecto.get(campo) != estado.get(campo):
                errores.append(f"'{campo}' no coincide entre proyecto.json y estado.json.")


def etiquetas_del_pr(explicitas):
    if explicitas is not None:
        return {e.strip() for e in explicitas.split(",") if e.strip()}
    ruta = os.environ.get("GITHUB_EVENT_PATH")
    if ruta and Path(ruta).exists():
        evento = json.loads(Path(ruta).read_text(encoding="utf-8"))
        return {e.get("name", "") for e in (evento.get("pull_request") or {}).get("labels", [])}
    return set()


def revisar_cambios(base, explicitas, errores, avisos):
    rc, salida = git("diff", "--name-only", f"{base}...HEAD")
    if rc != 0:
        errores.append(f"No se pudo comparar con la base {base}: {salida.strip()[:300]}")
        return
    cambiados = [l.strip() for l in salida.splitlines() if l.strip()]
    protegidos = [c for c in cambiados if c.startswith(PRUEBAS_ACEPTACION) and not c.endswith(".gitkeep")]
    if protegidos and ETIQUETA_PRUEBAS not in etiquetas_del_pr(explicitas):
        errores.append(
            f"Este cambio modifica pruebas de aceptación aprobadas ({len(protegidos)} archivo(s), por ejemplo "
            f"{protegidos[0]}). Solo la Dirección puede aprobarlo, con la etiqueta '{ETIQUETA_PRUEBAS}' en el PR.")
    rc, numstat = git("diff", "--numstat", f"{base}...HEAD")
    total = 0
    for linea in numstat.splitlines():
        partes = linea.split("\t")
        if len(partes) == 3 and partes[0].isdigit() and not partes[2].endswith(NO_CUENTAN):
            total += int(partes[0]) + int(partes[1])
    if total > LINEAS_UTILES:
        avisos.append(f"El cambio suma {total} líneas. Sobre {LINEAS_UTILES}, conviene dividirlo (constitución, artículo VIII).")


def main():
    preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="rama o commit base del PR, por ejemplo origin/main")
    ap.add_argument("--etiquetas", help="etiquetas del PR separadas por coma (para probar en local)")
    a = ap.parse_args()

    errores, avisos = [], []
    revisar_kit(errores)
    revisar_estado(errores)
    if a.base:
        revisar_cambios(a.base, a.etiquetas, errores, avisos)
    for aviso in avisos:
        print(f"Aviso: {aviso}")
    if errores:
        print("Verificación del proyecto con problemas:")
        print("\n".join(f"- {e}" for e in errores))
        return 1
    print("Verificación del proyecto: todo en orden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
