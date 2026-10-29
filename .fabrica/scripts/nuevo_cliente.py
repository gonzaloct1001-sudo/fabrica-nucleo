#!/usr/bin/env python3
"""Registra un cliente en esta instancia: crea clientes/<id>/cliente.md desde la plantilla.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/nuevo_cliente.py --id <slug> --nombre "<Nombre>" [--tipo empresa|holding|persona|propio]
        --negocio "<slug>:<rubro>:<descripción breve>" [--negocio ...]

Un holding lleva un --negocio por cada unidad. Un cliente con reserva estricta no se registra aquí: recibe su
propia instancia de la fábrica (nucleo/aislamiento.md).
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TIPOS = ("empresa", "holding", "persona", "propio")


def validar_slug(valor, que):
    if not SLUG.match(valor or ""):
        sys.exit(f"{que} '{valor}' no es válido: usa minúsculas, números y guiones, sin tildes ni espacios "
                 "(por ejemplo, distribuidora-norte).")


def leer_negocios(entradas):
    negocios = []
    for e in entradas:
        partes = [p.strip() for p in e.split(":", 2)]
        if len(partes) < 2:
            sys.exit(f"--negocio '{e}' debe tener la forma <slug>:<rubro>[:<descripción>].")
        validar_slug(partes[0], "El negocio")
        negocios.append((partes[0], partes[1], partes[2] if len(partes) > 2 else ""))
    if len({n[0] for n in negocios}) != len(negocios):
        sys.exit("Hay negocios repetidos.")
    return negocios


def armar_ficha(plantilla, cid, nombre, tipo, negocios):
    salida = []
    for linea in plantilla.splitlines():
        if linea.startswith("id:"):
            linea = f"id: {cid}"
        elif linea.startswith("tipo:"):
            linea = f"tipo: {tipo}"
        elif linea.startswith("reserva:"):
            linea = "reserva: estandar"
        elif linea.startswith("desde:"):
            linea = f"desde: {date.today().isoformat()}"
        elif linea.startswith("# <Nombre del cliente>"):
            linea = f"# {nombre}"
        elif linea.startswith("| <negocio> |"):
            salida.extend(f"| {s} | {r} | {d} |" for s, r, d in negocios)
            continue
        elif linea.startswith("| <proyecto> |"):
            continue
        salida.append(linea)
    return "\n".join(salida) + "\n"


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="identificador corto del cliente (slug)")
    ap.add_argument("--nombre", required=True, help="nombre legible del cliente")
    ap.add_argument("--tipo", default="empresa", choices=TIPOS)
    ap.add_argument("--reserva", default="estandar", choices=("estandar", "estricta"))
    ap.add_argument("--negocio", action="append", default=[], help="<slug>:<rubro>[:<descripción>], uno por negocio")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: los clientes se registran en una instancia, no aquí.")
    validar_slug(a.id, "El identificador del cliente")
    if a.reserva == "estricta":
        sys.exit("Un cliente con reserva estricta recibe su propia instancia de la fábrica, separada de esta "
                 "(nucleo/aislamiento.md). Crea esa instancia y regístralo allí.")
    negocios = leer_negocios(a.negocio)
    if not negocios:
        sys.exit("Indica al menos un --negocio (un holding lleva uno por cada unidad).")
    if a.tipo in ("empresa", "persona") and len(negocios) > 1:
        print(f"Aviso: un cliente de tipo '{a.tipo}' con varios negocios suele ser un holding.")

    ficha = RAIZ / "clientes" / a.id / "cliente.md"
    if ficha.exists():
        sys.exit(f"El cliente '{a.id}' ya existe: {ficha.relative_to(RAIZ).as_posix()}")
    plantilla = (RAIZ / "nucleo" / "plantillas" / "cliente.md").read_text(encoding="utf-8")
    ficha.parent.mkdir(parents=True, exist_ok=True)
    ficha.write_text(armar_ficha(plantilla, a.id, a.nombre, a.tipo, negocios), encoding="utf-8")
    print(f"Cliente registrado: {ficha.relative_to(RAIZ).as_posix()} ({len(negocios)} negocio(s)).")
    print("Completa en la ficha la contraparte y los acuerdos. Después crea su primer proyecto con nuevo_proyecto.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
