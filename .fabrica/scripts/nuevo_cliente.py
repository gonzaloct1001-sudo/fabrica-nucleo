#!/usr/bin/env python3
"""Registra un cliente en esta instancia: crea clientes/<id>/cliente.md desde la plantilla.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/nuevo_cliente.py --id <slug> --nombre "<Nombre>" [--tipo empresa|holding|persona|propio]
        --negocio "<slug>:<rubro>:<descripción breve>" [--negocio ...]
    python .fabrica/scripts/nuevo_cliente.py --id <slug> --agregar --negocio "<slug>:<rubro>:<descripción>"
        agrega negocios a un cliente ya registrado

Un holding lleva un --negocio por cada unidad. El rubro también es un slug (por ejemplo, gas-licuado o farmacia): si
la instancia todavía no tiene su base de conocimiento, se crea rubros/<rubro>/conocimiento.md desde la plantilla
(nucleo/aprendizaje.md). Un cliente con reserva estricta no se registra aquí: recibe su propia instancia de la fábrica
(nucleo/aislamiento.md).
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
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
        validar_slug(partes[1], "El rubro")
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


def agregar_a_ficha(ficha, negocios):
    """Agrega negocios a la tabla "Negocios" de una ficha que ya existe."""
    lineas = ficha.read_text(encoding="utf-8").splitlines()
    for i, linea in enumerate(lineas):
        if linea.startswith("| Negocio (slug) |"):
            j = i + 2
            while j < len(lineas) and lineas[j].startswith("|"):
                j += 1
            lineas[j:j] = [f"| {s} | {r} | {d} |" for s, r, d in negocios]
            ficha.write_text("\n".join(lineas) + "\n", encoding="utf-8")
            return
    sys.exit(f"La ficha {ficha.name} no tiene la tabla de negocios de la plantilla: agrégalos a mano.")


def crear_rubros(negocios):
    """Crea desde la plantilla la base de cada rubro que la instancia todavía no tenga."""
    plantilla = (RAIZ / "nucleo" / "plantillas" / "rubro.md").read_text(encoding="utf-8")
    for rubro in dict.fromkeys(r for _, r, _ in negocios):
        base = RAIZ / "rubros" / rubro / "conocimiento.md"
        if not base.exists():
            base.parent.mkdir(parents=True, exist_ok=True)
            base.write_text(plantilla.replace("<nombre del rubro>", rubro, 1), encoding="utf-8")
            print(f"Rubro nuevo: {base.relative_to(RAIZ).as_posix()}, desde la plantilla. Complétalo con lo que se sepa.")


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="identificador corto del cliente (slug)")
    ap.add_argument("--nombre", help="nombre legible del cliente (obligatorio al registrarlo)")
    ap.add_argument("--tipo", default="empresa", choices=TIPOS)
    ap.add_argument("--reserva", default="estandar", choices=("estandar", "estricta"))
    ap.add_argument("--negocio", action="append", default=[], help="<slug>:<rubro>[:<descripción>], uno por negocio")
    ap.add_argument("--agregar", action="store_true", help="agregar negocios a un cliente ya registrado")
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
    if a.agregar:
        if not ficha.exists():
            sys.exit(f"El cliente '{a.id}' no está registrado: regístralo sin --agregar.")
        repetidos = [s for s, _, _ in negocios if s in _kit.negocios(ficha)]
        if repetidos:
            sys.exit(f"El cliente '{a.id}' ya tiene el negocio '{repetidos[0]}'.")
        agregar_a_ficha(ficha, negocios)
        print(f"Negocios agregados a {ficha.relative_to(RAIZ).as_posix()}: {', '.join(s for s, _, _ in negocios)}.")
        crear_rubros(negocios)
        return 0
    if ficha.exists():
        sys.exit(f"El cliente '{a.id}' ya existe: {ficha.relative_to(RAIZ).as_posix()}. Para sumarle negocios, usa "
                 "--agregar.")
    if not a.nombre:
        sys.exit("Indica el --nombre del cliente.")
    plantilla = (RAIZ / "nucleo" / "plantillas" / "cliente.md").read_text(encoding="utf-8")
    ficha.parent.mkdir(parents=True, exist_ok=True)
    ficha.write_text(armar_ficha(plantilla, a.id, a.nombre, a.tipo, negocios), encoding="utf-8")
    print(f"Cliente registrado: {ficha.relative_to(RAIZ).as_posix()} ({len(negocios)} negocio(s)).")
    crear_rubros(negocios)
    print("Completa en la ficha la contraparte y los acuerdos. Después crea su primer proyecto con nuevo_proyecto.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
