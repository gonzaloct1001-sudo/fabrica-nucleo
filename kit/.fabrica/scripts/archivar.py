#!/usr/bin/env python3
"""Archiva lo que ya no hace falta leer de una historia cerrada (núcleo 0.13, punto A5).

Uso, desde la raíz del proyecto:
    python .fabrica/scripts/archivar.py H-001            muestra qué movería
    python .fabrica/scripts/archivar.py H-001 --aplicar  lo mueve con `git mv`

Mueve a `docs/archivo/` el plan de la historia (archivo o carpeta) y su modelo de amenazas por historia, si existe.
La historia misma no se mueve: sigue contando en el estado. Los agentes no leen `docs/archivo/` salvo que la tarea lo
pida, así que cada lectura de rutina pesa menos. Solo archiva historias en estado `hecho`. Nada se borra: todo queda
en git y en su nueva carpeta.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import estado as _estado  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO = "docs/archivo"


def que_mover(raiz, identificador):
    """[(origen, destino)] relativos al proyecto, y el problema si no se puede archivar."""
    proyecto = _estado.leer_json(raiz / ".fabrica/proyecto.json")
    rutas = _estado.rutas_del_proyecto(proyecto, raiz)
    historia = None
    for ruta in sorted((raiz / rutas["historias"]).glob(f"{identificador}-*.md")):
        cabecera = _estado.leer_cabecera(_estado.leer(ruta))
        if cabecera.get("id") == identificador:
            historia = cabecera
            break
    if not historia:
        return [], f"No encuentro la historia {identificador} en {rutas['historias']}/."
    if historia.get("estado") != "hecho":
        return [], f"{identificador} está en «{historia.get('estado', '?')}»: solo se archiva una historia hecha."
    candidatos = [f"{rutas['planes']}/{identificador}-plan.md", f"{rutas['planes']}/{identificador}",
                  f"docs/seguridad/historias/{identificador}.md"]
    movimientos = []
    for origen in candidatos:
        if (raiz / origen).exists():
            destino = f"{ARCHIVO}/{origen[len('docs/'):] if origen.startswith('docs/') else origen}"
            movimientos.append((origen, destino))
    if not movimientos:
        return [], f"{identificador} no tiene plan ni modelo de amenazas propio que archivar."
    return movimientos, None


def main(argumentos=None, raiz=RAIZ):
    analizador = argparse.ArgumentParser(description="Archiva el plan y el modelo de amenazas de una historia hecha.")
    analizador.add_argument("historia", help="identificador, por ejemplo H-001")
    analizador.add_argument("--aplicar", action="store_true", help="mueve los archivos con git mv")
    opciones = analizador.parse_args(argumentos)
    movimientos, problema = que_mover(raiz, opciones.historia.strip().upper())
    if problema:
        print(problema)
        return 1
    for origen, destino in movimientos:
        print(f"{origen} -> {destino}")
        if opciones.aplicar:
            (raiz / destino).parent.mkdir(parents=True, exist_ok=True)
            hecho = subprocess.run(["git", "mv", origen, destino], cwd=raiz, capture_output=True, text=True,
                                   check=False)
            if hecho.returncode != 0:
                print(f"No se pudo mover {origen}: {hecho.stderr.strip()}")
                return 1
    print("Archivado." if opciones.aplicar else "Vista previa: agrega --aplicar para moverlos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
