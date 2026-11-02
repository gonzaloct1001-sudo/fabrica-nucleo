#!/usr/bin/env python3
"""Crea un proyecto de un cliente: un repositorio nuevo con el kit de la fábrica ya armado.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/nuevo_proyecto.py --cliente <slug> --negocio <slug> --proyecto <slug> [--nombre "<Nombre>"]
        [--destino <carpeta>] [--sin-git] [--github]

- El cliente debe estar registrado (nuevo_cliente.py) y el negocio, en su ficha.
- Por defecto, el proyecto se crea en proyectos/<cliente>-<proyecto>/ con su propio repositorio Git y un primer
  commit. Con --github, crea además el repositorio privado en la cuenta de config.json y sus etiquetas.
- El kit es lo que trae kit/ más una copia del método (nucleo/ → .fabrica/nucleo/) y la base del rubro del negocio
  (rubros/<rubro>/ → .fabrica/rubro/). Su manifiesto queda registrado para poder actualizarlo después sin tocar lo
  propio del proyecto.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validar_slug(valor, que):
    if not SLUG.match(valor or ""):
        sys.exit(f"{que} '{valor}' no es válido: usa minúsculas, números y guiones, sin tildes ni espacios.")


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def armar_kit(destino, cliente, negocio, proyecto, nombre, propietario):
    """Arma en `destino` el kit de la fábrica y los archivos iniciales del proyecto."""
    version = _nucleo.version(RAIZ)
    _kit.armar(RAIZ, destino, _kit.rubro_de(RAIZ, cliente, negocio))
    _kit.preparar_proyecto(RAIZ, destino, cliente, negocio, proyecto, nombre, propietario, version)
    _nucleo.escribir_manifiesto(destino, _nucleo.archivos(destino))


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--negocio", required=True)
    ap.add_argument("--proyecto", required=True)
    ap.add_argument("--nombre", help="nombre legible del proyecto (por defecto, el identificador)")
    ap.add_argument("--destino", help="carpeta donde crearlo (por defecto, proyectos/<cliente>-<proyecto>)")
    ap.add_argument("--sin-git", action="store_true", help="no crear el repositorio Git local")
    ap.add_argument("--github", action="store_true", help="crear también el repositorio privado en GitHub")
    a = ap.parse_args()

    for valor, que in ((a.cliente, "El cliente"), (a.negocio, "El negocio"), (a.proyecto, "El proyecto")):
        validar_slug(valor, que)
    ficha = RAIZ / "clientes" / a.cliente / "cliente.md"
    if not ficha.exists():
        sys.exit(f"El cliente '{a.cliente}' no está registrado. Regístralo primero con nuevo_cliente.py.")
    if a.negocio not in _kit.negocios(ficha):
        sys.exit(f"El negocio '{a.negocio}' no está en la ficha de '{a.cliente}'. Agrégalo a su tabla de negocios.")

    repo = f"{a.cliente}-{a.proyecto}"
    destino = Path(a.destino).resolve() if a.destino else RAIZ / "proyectos" / repo
    if destino.exists() and any(destino.iterdir()):
        sys.exit(f"Ya existe {destino} y no está vacía.")
    if _nucleo.es_mantenedor(RAIZ) and RAIZ.resolve() in destino.resolve().parents:
        sys.exit("Esta carpeta es el núcleo que mantienes: los proyectos se crean desde una instancia, no aquí.")

    propietario = ""
    config = RAIZ / ".fabrica" / "config.json"
    if config.exists():
        propietario = (json.loads(config.read_text(encoding="utf-8")).get("github") or {}).get("propietario", "")

    destino.mkdir(parents=True, exist_ok=True)
    armar_kit(destino, a.cliente, a.negocio, a.proyecto, a.nombre or a.proyecto, propietario)
    _kit.anotar_en_ficha(ficha, a.cliente, a.negocio, a.proyecto)
    print(f"Proyecto creado en {destino} con el kit de la fábrica (núcleo {_nucleo.version(RAIZ)}).")
    rubro = _kit.rubro_de(RAIZ, a.cliente, a.negocio)
    if not (RAIZ / "rubros" / rubro).is_dir():
        print(f"Aviso: la instancia no tiene base del rubro '{rubro}' (rubros/{rubro}/). El proyecto parte sin ella.")

    if not a.sin_git:
        git(destino, "init", "-q", "-b", "main")
        git(destino, "add", "-A")
        rc, salida = git(destino, "commit", "-q", "-m", f"Crea el proyecto {repo} desde la fábrica {_nucleo.version(RAIZ)}")
        print("Repositorio Git creado con su primer commit." if rc == 0 else f"No se hizo el primer commit: {salida[:300]}")

    if a.github:
        if not propietario:
            sys.exit("Para --github falta 'github.propietario' en .fabrica/config.json.")
        r = subprocess.run(["gh", "repo", "create", f"{propietario}/{repo}", "--private", "--source", str(destino),
                            "--remote", "origin", "--push"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0:
            sys.exit(f"No se pudo crear el repositorio en GitHub: {(r.stderr or r.stdout).strip()[:400]}")
        print(f"Repositorio privado creado: https://github.com/{propietario}/{repo}")
        subprocess.run([sys.executable, ".fabrica/scripts/crear_etiquetas.py"], cwd=destino)

    print("Siguiente paso: abrir el proyecto con el asistente y describir el primer pedido. La skill triage lo clasifica.")
    print("Recuerda hacer commit de la ficha del cliente en la instancia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
