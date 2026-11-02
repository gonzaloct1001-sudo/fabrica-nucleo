"""Cómo se arma el kit de proyecto: lo mismo al crear un proyecto (nuevo_proyecto.py) y al actualizarlo
(actualizar_kit.py).

El kit es lo que trae kit/ más una copia del método y la base del rubro del proyecto:
- nucleo/ va a .fabrica/nucleo/;
- rubros/<rubro>/ de la instancia va a .fabrica/rubro/. Si la instancia todavía no tiene esa base, va un aviso en su
  lugar, para que la ruta exista siempre (nucleo/aprendizaje.md).
"""
import re
import shutil
from pathlib import Path

import _nucleo

COPIA_DEL_METODO = Path(".fabrica") / "nucleo"
COPIA_DEL_RUBRO = Path(".fabrica") / "rubro"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SIN_BASE = """# Rubro: {rubro}

La fábrica todavía no tiene una base de conocimiento de este rubro. Se crea en la instancia, en `rubros/{rubro}/`,
desde `.fabrica/nucleo/plantillas/rubro.md`, y llega aquí con la siguiente actualización del kit.

Mientras tanto, el descubrimiento parte de cero: todo lo que el pedido no diga es una pregunta.
"""


def copiar_arbol(origen, destino):
    origen, destino = Path(origen), Path(destino)
    for x in sorted(origen.rglob("*")):
        rel = x.relative_to(origen)
        if x.is_file() and not (set(rel.parts) & _nucleo.IGNORAR_PARTES) and rel.name not in _nucleo.IGNORAR_NOMBRES \
                and x.suffix != ".pyc":
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x, destino / rel)


def tabla(ficha, seccion):
    """Filas de la tabla bajo `## <seccion>` de una ficha de cliente, como listas de celdas (sin encabezado)."""
    filas, dentro = [], False
    for linea in Path(ficha).read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            dentro = linea.strip() == f"## {seccion}"
            continue
        if dentro and linea.startswith("|"):
            celdas = [c.strip().strip("`") for c in linea.strip().strip("|").split("|")]
            if celdas and SLUG.match(celdas[0]):
                filas.append(celdas)
    return filas


def negocios(ficha):
    """{negocio: rubro} de la tabla "Negocios" de una ficha de cliente."""
    return {f[0]: f[1] for f in tabla(ficha, "Negocios") if len(f) >= 2}


def rubro_de(raiz_instancia, cliente, negocio):
    """Rubro del negocio según la ficha del cliente, o cadena vacía si no se encuentra."""
    ficha = Path(raiz_instancia) / "clientes" / cliente / "cliente.md"
    return negocios(ficha).get(negocio, "") if ficha.exists() else ""


def armar(raiz_instancia, destino, rubro=""):
    """Copia en `destino` el kit de la instancia, con su copia del método y la base del rubro."""
    raiz_instancia, destino = Path(raiz_instancia), Path(destino)
    copiar_arbol(raiz_instancia / "kit", destino)
    copiar_arbol(raiz_instancia / "nucleo", destino / COPIA_DEL_METODO)
    base = raiz_instancia / "rubros" / rubro if rubro and SLUG.match(rubro) else None
    if base and base.is_dir() and any(base.rglob("*.md")):
        copiar_arbol(base, destino / COPIA_DEL_RUBRO)
    else:
        (destino / COPIA_DEL_RUBRO).mkdir(parents=True, exist_ok=True)
        (destino / COPIA_DEL_RUBRO / "conocimiento.md").write_text(SIN_BASE.format(rubro=rubro or "sin definir"),
                                                                  encoding="utf-8")
