#!/usr/bin/env python3
"""Adopta en la fábrica un proyecto que ya existe: le instala el kit sin perder su historia ni lo que ya tenía.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/adoptar_proyecto.py <carpeta del repositorio> --cliente <slug> --negocio <slug>
        --proyecto <slug> [--nombre "<Nombre>"] [--fase descubrimiento|especificacion|construccion|...]
        vista previa: no cambia nada
    ... --aplicar [--sin-commit]

- El cliente debe estar registrado y el negocio, en su ficha. El repositorio debería llamarse <cliente>-<proyecto>;
  si no, renómbralo después (en GitHub, el nombre anterior redirige al nuevo).
- Instala el kit (agentes, skills, método, base del rubro, motor y CI de la fábrica) y crea solo los archivos propios
  que falten: .fabrica/proyecto.json, .fabrica/estado.json, docs/constitucion.md, docs/bitacora.md y sus carpetas.
  Nunca pisa el código, el README, docs/ ni la CI propia. Al .gitignore solo le agrega las líneas que le falten.
- Si un archivo del proyecto ocupa una ruta del kit (por ejemplo, su propio CLAUDE.md o un agente con el mismo nombre),
  lo respalda en .fabrica/respaldo-nucleo/<fecha>/ antes de reemplazarlo. Lo que ese archivo decía (reglas propias,
  por ejemplo) se lleva a docs/constitucion.md, idealmente antes de adoptar.
- Los archivos propios dentro de carpetas del kit (un agente o una skill que el kit no trae) se conservan. Conviene
  decidir para cada uno si sigue, si pasa a llamarse local-* o si su conocimiento va a la base del rubro.
- Exige el repositorio sin cambios sin commit. Verifica con verificar_proyecto.py y, si falla, deja todo como estaba.
  Termina con un commit; subirlo e integrarlo sigue la regla de "Quién integra cada PR" (nucleo/autonomia.md).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _actualizacion  # noqa: E402
import _kit  # noqa: E402
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FASES = ("descubrimiento", "especificacion", "construccion", "estabilizacion", "operacion")


def archivos_del_proyecto(raiz):
    """{ruta en minúsculas: ruta real} de los archivos del proyecto, fuera de .git y de las carpetas ignoradas."""
    salida = {}
    for x in raiz.rglob("*"):
        rel = x.relative_to(raiz)
        if x.is_file() and not (set(rel.parts) & _nucleo.IGNORAR_PARTES):
            salida[rel.as_posix().lower()] = rel.as_posix()
    return salida


def lista(titulo, items, maximo=20):
    if not items:
        return []
    salida = [f"- {titulo}: {len(items)}"] + [f"  - {i}" for i in items[:maximo]]
    return salida + ([f"  - … y {len(items) - maximo} más"] if len(items) > maximo else [])


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", help="carpeta del repositorio que se adopta")
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--negocio", required=True)
    ap.add_argument("--proyecto", required=True)
    ap.add_argument("--nombre", help="nombre legible del proyecto (por defecto, el identificador)")
    ap.add_argument("--fase", default="descubrimiento", choices=FASES, help="fase en que está hoy el proyecto")
    ap.add_argument("--aplicar", action="store_true", help="adoptar (sin esto, solo vista previa)")
    ap.add_argument("--sin-commit", action="store_true", help="no hacer el commit de la adopción")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: los proyectos se adoptan desde una instancia, no aquí.")
    for valor, que in ((a.cliente, "El cliente"), (a.negocio, "El negocio"), (a.proyecto, "El proyecto")):
        if not SLUG.match(valor):
            sys.exit(f"{que} '{valor}' no es válido: usa minúsculas, números y guiones, sin tildes ni espacios.")
    ficha = RAIZ / "clientes" / a.cliente / "cliente.md"
    if not ficha.exists():
        sys.exit(f"El cliente '{a.cliente}' no está registrado. Regístralo primero con nuevo_cliente.py.")
    if a.negocio not in _kit.negocios(ficha):
        sys.exit(f"El negocio '{a.negocio}' no está en la ficha de '{a.cliente}'. Agrégalo con "
                 f"nuevo_cliente.py --id {a.cliente} --agregar --negocio <slug>:<rubro>[:<descripción>].")
    raiz = Path(a.carpeta)
    raiz = (raiz if raiz.is_absolute() else Path.cwd() / raiz).resolve()
    if not raiz.is_dir():
        sys.exit(f"No existe la carpeta {raiz}.")
    if (raiz / ".fabrica" / "proyecto.json").exists() or (raiz / "NUCLEO.txt").exists():
        sys.exit(f"{raiz.name} ya es un proyecto de la fábrica: para traerle el kit nuevo, usa actualizar_kit.py.")
    if RAIZ.resolve() == raiz or (RAIZ.resolve() in raiz.parents and "proyectos" not in raiz.relative_to(RAIZ).parts):
        sys.exit("Esa carpeta es parte de la instancia, no un proyecto.")
    if a.aplicar:
        _actualizacion.exigir_arbol_limpio(raiz)

    version = _nucleo.version(RAIZ)
    rubro = _kit.rubro_de(RAIZ, a.cliente, a.negocio)
    repo = f"{a.cliente}-{a.proyecto}"
    propietario = ""
    config = RAIZ / ".fabrica" / "config.json"
    if config.exists():
        propietario = (json.loads(config.read_text(encoding="utf-8")).get("github") or {}).get("propietario", "")

    with tempfile.TemporaryDirectory(prefix="fabrica-adopcion-") as tmp:
        fuente = Path(tmp) / "kit"
        _kit.armar(RAIZ, fuente, rubro)
        kit = _nucleo.archivos(fuente)
        existentes = archivos_del_proyecto(raiz)
        nuevos, reemplazos, choques = [], [], []
        for rel, h in kit.items():
            real = existentes.get(rel.lower())
            if real is None:
                nuevos.append(rel)
            elif real != rel:
                choques.append(real)  # misma ruta salvo mayúsculas: en Windows y macOS son el mismo archivo
            elif _nucleo.huella(raiz / rel) != h:
                reemplazos.append(rel)
        carpetas_kit = [e for e in _nucleo.rutas(fuente) if e.endswith("/")]
        en_kit = {r.lower() for r in kit}
        propios = sorted(real for bajo, real in existentes.items()
                         if bajo not in en_kit and any(bajo.startswith(c.lower()) for c in carpetas_kit))

        out = [f"# Adopción en la fábrica · {raiz.name}", "",
               f"- Proyecto: {repo} (cliente {a.cliente}, negocio {a.negocio}, rubro {rubro or 'sin definir'}, "
               f"fase {a.fase})", f"- Kit del núcleo {version}: {len(kit)} archivos"]
        if raiz.name != repo:
            out.append(f"- El repositorio se llama {raiz.name}: renómbralo a {repo} después de adoptarlo.")
        out += lista("Nuevos del kit", nuevos, 10)
        out += lista("Del proyecto, que el kit reemplaza (se respaldan; lleva lo que digan a docs/constitucion.md)",
                     reemplazos + choques)
        out += lista("Propios dentro de carpetas del kit (se conservan; decide si siguen, pasan a local-* o a la "
                     "base del rubro)", propios)
        faltan = [r for r in (".fabrica/proyecto.json", ".fabrica/estado.json", "docs/constitucion.md",
                              "docs/bitacora.md", "README.md", ".env.example", ".gitignore")
                  if r.lower() not in existentes]
        out += lista("Archivos propios que se crean", faltan)
        out.append("- No se tocan: el código, docs/ (salvo lo que falte), la CI propia ni el README existente.")
        if not a.aplicar:
            out += ["", "Vista previa: nada cambió. Para adoptar, repite el comando con --aplicar."]
            print("\n".join(out))
            return 0
        print("\n".join(out))

        sello = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        respaldo = raiz / ".fabrica" / "respaldo-nucleo" / sello
        for rel in reemplazos + choques:
            (respaldo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raiz / rel, respaldo / rel)
        for rel in choques:
            (raiz / rel).unlink()
        for rel in nuevos + reemplazos:
            (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fuente / rel, raiz / rel)
        for real in choques:
            rel = next(r for r in kit if r.lower() == real.lower())
            (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fuente / rel, raiz / rel)
        creados, gitignore_previo = _kit.preparar_proyecto(RAIZ, raiz, a.cliente, a.negocio, a.proyecto,
                                                           a.nombre or a.proyecto, propietario, version,
                                                           fase=a.fase, adoptado=True)
        _nucleo.escribir_manifiesto(raiz, kit)

        def revertir():
            for rel in nuevos + creados + [r for r in kit if r.lower() in {c.lower() for c in choques}]:
                (raiz / rel).unlink(missing_ok=True)
            for x in respaldo.rglob("*"):
                if x.is_file():
                    shutil.copy2(x, raiz / x.relative_to(respaldo))
            if gitignore_previo is not None:
                (raiz / ".gitignore").write_text(gitignore_previo, encoding="utf-8")
            (raiz / _nucleo.MANIFIESTO).unlink(missing_ok=True)
            shutil.rmtree(respaldo, ignore_errors=True)

        print(f"\nAplicado. Respaldo de lo reemplazado: {respaldo.relative_to(raiz).as_posix()}/")
        print("Verificando el proyecto adoptado...")
        r = subprocess.run([sys.executable, ".fabrica/scripts/verificar_proyecto.py"], cwd=raiz, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=600)
        salida = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode != 0:
            revertir()
            print("La verificación falló: se deshizo la adopción. Nada cambió.\n" + "\n".join(salida.splitlines()[-15:]))
            return 1
        print((salida.splitlines() or ["Verificación: sin salida"])[-1])

    _kit.anotar_en_ficha(ficha, a.cliente, a.negocio, a.proyecto)
    print(f"La ficha del cliente lista el proyecto: {ficha.relative_to(RAIZ).as_posix()}. Haz commit en la instancia.")
    if _actualizacion.es_repositorio(raiz):
        # En Windows y macOS, git no registra un cambio que es solo de mayúsculas: sin esto, el índice conserva el
        # nombre anterior y en Linux falta la ruta del kit
        for real in choques:
            _actualizacion.git(raiz, "rm", "--cached", "-q", "--ignore-unmatch", "--", real)
    if _actualizacion.es_repositorio(raiz) and not a.sin_commit:
        _actualizacion.git(raiz, "add", "-A")
        mensaje = f"Adopta el proyecto en la fábrica (núcleo {version})"
        rc, salida_c = _actualizacion.git(raiz, "commit", "-q", "-m", mensaje)
        print(f"Commit: «{mensaje}»." if rc == 0 else f"No se hizo el commit: {salida_c[:400]}")
        if rc == 0:
            print("Para deshacer la adopción completa: git revert HEAD")
    if reemplazos or choques:
        print("Revisa lo reemplazado: su versión anterior quedó en el respaldo. Si tenía reglas propias, llévalas a "
              "docs/constitucion.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
