#!/usr/bin/env python3
"""Crea un proyecto de un cliente: un repositorio nuevo con el kit de la fábrica ya armado.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/nuevo_proyecto.py --cliente <slug> --negocio <slug> --proyecto <slug> [--nombre "<Nombre>"]
        [--destino <carpeta>] [--sin-git] [--github]

- El cliente debe estar registrado (nuevo_cliente.py) y el negocio, en su ficha.
- Por defecto, el proyecto se crea en proyectos/<cliente>-<proyecto>/ con su propio repositorio Git y un primer
  commit. Con --github, crea además el repositorio privado en la cuenta de config.json y sus etiquetas.
- El kit es lo que trae kit/ más una copia del método (nucleo/ → .fabrica/nucleo/). Su manifiesto queda registrado
  para poder actualizarlo después sin tocar lo propio del proyecto.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

GITIGNORE = """# Entorno y secretos
.env
.env.*
!.env.example

# Archivos de trabajo de la fábrica (fichas, informes y diffs de cada corrida)
.fabrica/trabajo/
.fabrica/respaldo-nucleo/

# Configuración personal del asistente
.claude/settings.local.json

# Sistema
.DS_Store
Thumbs.db
desktop.ini
"""


def validar_slug(valor, que):
    if not SLUG.match(valor or ""):
        sys.exit(f"{que} '{valor}' no es válido: usa minúsculas, números y guiones, sin tildes ni espacios.")


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def copiar_arbol(origen, destino):
    for x in sorted(Path(origen).rglob("*")):
        rel = x.relative_to(origen)
        if x.is_file() and not (set(rel.parts) & _nucleo.IGNORAR_PARTES) and rel.name not in _nucleo.IGNORAR_NOMBRES:
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x, destino / rel)


def armar_kit(destino, cliente, negocio, proyecto, nombre, propietario):
    """Arma en `destino` el kit de la fábrica y los archivos iniciales del proyecto."""
    version = _nucleo.version(RAIZ)
    copiar_arbol(RAIZ / "kit", destino)
    copiar_arbol(RAIZ / "nucleo", destino / ".fabrica" / "nucleo")

    repo = f"{cliente}-{proyecto}"
    hoy = date.today().isoformat()
    datos = {"version_formato": 1, "cliente": cliente, "negocio": negocio, "proyecto": proyecto, "nombre": nombre,
             "repositorio": repo, "nucleo": version, "creado": hoy, "pausa": False}
    (destino / ".fabrica" / "proyecto.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                                                        encoding="utf-8")

    estado = json.loads((RAIZ / "nucleo" / "plantillas" / "estado.json").read_text(encoding="utf-8"))
    estado = {k: v for k, v in estado.items() if not k.startswith("_")}
    estado.update({"cliente": cliente, "negocio": negocio, "proyecto": proyecto, "nucleo": version,
                   "fase": "descubrimiento", "semaforo": "verde", "riesgo_principal": "",
                   "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    estado["espera_direccion"]["enlace"] = (
        f"https://github.com/{propietario}/{repo}/issues?q=label%3Aespera%3Adireccion" if propietario else "")
    (destino / ".fabrica" / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")

    constitucion = (RAIZ / "nucleo" / "plantillas" / "constitucion-proyecto.md").read_text(encoding="utf-8")
    constitucion = constitucion.replace("# Constitución de <proyecto>", f"# Constitución de {nombre}", 1)
    constitucion = constitucion.replace("<AAAA-MM-DD>", hoy, 1)
    (destino / "docs").mkdir(parents=True, exist_ok=True)
    (destino / "docs" / "constitucion.md").write_text(constitucion, encoding="utf-8")
    (destino / "docs" / "bitacora.md").write_text(
        f"# Bitácora\n\n## {hoy}\n\n- Proyecto creado desde la fábrica (núcleo {version}).\n", encoding="utf-8")
    for carpeta in ("docs/historias", "docs/planes", "docs/adr", "docs/descubrimiento", "pruebas/aceptacion"):
        (destino / carpeta).mkdir(parents=True, exist_ok=True)
        (destino / carpeta / ".gitkeep").write_text("", encoding="utf-8")
    (destino / "README.md").write_text(
        f"# {nombre}\n\nProyecto construido con una fábrica de software. Las instrucciones para agentes están en "
        f"`AGENTS.md`; el método, en `.fabrica/nucleo/`; las historias, en `docs/historias/`.\n", encoding="utf-8")
    (destino / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (destino / ".env.example").write_text("# Variables de entorno del proyecto. Nunca pongas valores reales aquí.\n",
                                          encoding="utf-8")
    _nucleo.escribir_manifiesto(destino, _nucleo.archivos(destino))


def anotar_en_ficha(ficha, cliente, negocio, proyecto):
    lineas = ficha.read_text(encoding="utf-8").splitlines()
    for i, linea in enumerate(lineas):
        if linea.startswith("| Proyecto | Negocio | Repositorio | Estado |"):
            j = i + 2
            while j < len(lineas) and lineas[j].startswith("|"):
                j += 1
            lineas.insert(j, f"| {proyecto} | {negocio} | `{cliente}-{proyecto}` | activo |")
            ficha.write_text("\n".join(lineas) + "\n", encoding="utf-8")
            return True
    return False


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
    if not re.search(rf"^\|\s*{re.escape(a.negocio)}\s*\|", ficha.read_text(encoding="utf-8"), re.M):
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
    anotar_en_ficha(ficha, a.cliente, a.negocio, a.proyecto)
    print(f"Proyecto creado en {destino} con el kit de la fábrica (núcleo {_nucleo.version(RAIZ)}).")

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
