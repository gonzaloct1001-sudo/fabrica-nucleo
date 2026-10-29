"""Cómo se arma el kit de proyecto: lo mismo al crear un proyecto (nuevo_proyecto.py) y al actualizarlo
(actualizar_kit.py).

El kit es lo que trae kit/ más una copia del método: nucleo/ va a .fabrica/nucleo/ dentro del proyecto.
"""
import shutil
from pathlib import Path

import _nucleo

COPIA_DEL_METODO = Path(".fabrica") / "nucleo"


def copiar_arbol(origen, destino):
    origen, destino = Path(origen), Path(destino)
    for x in sorted(origen.rglob("*")):
        rel = x.relative_to(origen)
        if x.is_file() and not (set(rel.parts) & _nucleo.IGNORAR_PARTES) and rel.name not in _nucleo.IGNORAR_NOMBRES \
                and x.suffix != ".pyc":
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x, destino / rel)


def armar(raiz_instancia, destino):
    """Copia en `destino` el kit de la instancia, con su copia del método."""
    raiz_instancia, destino = Path(raiz_instancia), Path(destino)
    copiar_arbol(raiz_instancia / "kit", destino)
    copiar_arbol(raiz_instancia / "nucleo", destino / COPIA_DEL_METODO)
