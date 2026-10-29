#!/usr/bin/env python3
"""Actualiza el núcleo de la fábrica en esta instancia sin tocar lo propio.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/actualizar_nucleo.py [--desde <url | carpeta>]              vista previa: no cambia nada
    python .fabrica/scripts/actualizar_nucleo.py [--desde <url | carpeta>] --aplicar [--sin-commit]

- Origen: --desde, o la línea "# origen:" de NUCLEO.txt. Puede ser la URL del repositorio del núcleo (se descarga una
  copia temporal) o una carpeta (por ejemplo, un zip descomprimido de la versión nueva).
- Solo cambia las rutas de NUCLEO.txt. Nunca toca clientes/, instancia/, proyectos/ ni .fabrica/config.json (salvo
  la versión del núcleo que registra), ni los archivos propios que la instancia agregó dentro de carpetas del núcleo.
- Con --aplicar exige que no haya cambios sin commit: así la actualización queda en un commit propio, fácil de revisar
  y de deshacer con git revert.
- Respalda en .fabrica/respaldo-nucleo/<fecha>/ todo lo que reemplaza o elimina. Los archivos del núcleo que se
  modificaron a mano se respaldan y se avisan.
- Después de aplicar corre .fabrica/scripts/verificar.py. Si falla, revierte todo y nada cambia.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
NUNCA = ("clientes/", "instancia/", "proyectos/", ".fabrica/config.json", ".fabrica/nucleo-instalado.csv",
         ".fabrica/respaldo-nucleo/")
CONFIG = RAIZ / ".fabrica" / "config.json"


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def es_repositorio():
    rc, top = git("rev-parse", "--show-toplevel")
    return rc == 0 and Path(top).resolve() == RAIZ.resolve()


def obtener_fuente(origen, tmp):
    p = Path(origen).expanduser()
    if p.is_dir():
        return p.resolve()
    destino = Path(tmp) / "nucleo"
    r = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.longpaths=true", "clone", "-q", "--depth", "1",
                        origen, str(destino)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"No se pudo descargar el núcleo desde {origen}:\n{(r.stderr or r.stdout).strip()[:500]}")
    return destino


def plan(fuente):
    entradas_nuevas = _nucleo.rutas(fuente)
    entradas_locales = _nucleo.rutas(RAIZ) if (RAIZ / "NUCLEO.txt").exists() else []
    union = list(dict.fromkeys(entradas_locales + entradas_nuevas))
    union = [e for e in union if not any(e.startswith(n) for n in NUNCA)]
    nuevos = _nucleo.archivos(fuente, [e for e in entradas_nuevas if e in union])
    locales = _nucleo.archivos(RAIZ, union)
    manifiesto = _nucleo.leer_manifiesto(RAIZ)
    p = {"agregar": [], "reemplazar": [], "iguales": 0, "eliminar": [], "modificados": [], "propios": [], "revisar": [],
         "nuevos": nuevos, "union": union}
    for rel, h in nuevos.items():
        if rel not in locales:
            p["agregar"].append(rel)
        elif locales[rel] != h:
            p["reemplazar"].append(rel)
            if manifiesto and rel in manifiesto and manifiesto[rel] != locales[rel]:
                p["modificados"].append(rel)
        else:
            p["iguales"] += 1
    for rel, h in locales.items():
        if rel in nuevos:
            continue
        if manifiesto is None:
            p["revisar"].append(rel)
        elif rel not in manifiesto:
            p["propios"].append(rel)
        elif manifiesto[rel] == h:
            p["eliminar"].append(rel)
        else:
            p["modificados"].append(rel)
            p["propios"].append(rel)
    return p


def lista(titulo, items, maximo=15):
    if not items:
        return []
    salida = [f"- {titulo}: {len(items)}"]
    salida += [f"  - {x}" for x in items[:maximo]]
    if len(items) > maximo:
        salida.append(f"  - … y {len(items) - maximo} más")
    return salida


def registrar_version(v_nueva):
    """Anota la versión del núcleo en config.json sin tocar el resto del archivo."""
    if CONFIG.exists() and v_nueva:
        texto = CONFIG.read_text(encoding="utf-8")
        texto = re.sub(r'("nucleo_version"\s*:\s*")[^"]*(")', rf"\g<1>{v_nueva}\g<2>", texto, count=1)
        CONFIG.write_text(texto, encoding="utf-8")


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", help="URL del repositorio del núcleo o carpeta con la versión nueva")
    ap.add_argument("--aplicar", action="store_true", help="aplicar la actualización (sin esto, solo vista previa)")
    ap.add_argument("--sin-commit", action="store_true", help="no hacer el commit de la actualización")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: se actualiza con Git (pull y push), no con este comando.")
    origen = a.desde or _nucleo.origen_oficial(RAIZ)
    if not origen:
        sys.exit("No sé de dónde traer el núcleo: indica --desde <url o carpeta>.")
    repo = es_repositorio()
    if a.aplicar and repo:
        rc, sucio = git("status", "--porcelain")
        if rc == 0 and sucio:
            sys.exit("Hay cambios sin commit en la instancia. Haz commit o guárdalos aparte antes de actualizar, "
                     "para que la actualización quede en un commit propio y se pueda revertir.\n" + sucio[:800])

    with tempfile.TemporaryDirectory(prefix="fabrica-nucleo-") as tmp:
        fuente = obtener_fuente(origen, tmp)
        if fuente.resolve() == RAIZ.resolve():
            sys.exit("El origen es esta misma carpeta: indica la carpeta o el repositorio del núcleo nuevo.")
        p = plan(fuente)
        v_local, v_nueva = _nucleo.version(RAIZ), _nucleo.version(fuente)
        out = ["# Actualización del núcleo", "", f"- Origen: {origen}", f"- Versión: {v_local or '?'} → {v_nueva or '?'}",
               f"- Archivos: {len(p['agregar'])} nuevos · {len(p['reemplazar'])} cambiados · "
               f"{len(p['eliminar'])} eliminados · {p['iguales']} iguales"]
        out += lista("Nuevos", p["agregar"]) + lista("Cambiados", p["reemplazar"])
        out += lista("Eliminados (el núcleo nuevo ya no los trae)", p["eliminar"])
        out += lista("Modificados a mano en esta instancia (se respaldan antes de reemplazarlos)", p["modificados"])
        out += lista("Propios de la instancia dentro de carpetas del núcleo (se conservan)", p["propios"])
        out += lista("Sin registro del núcleo instalado: no se borran, revísalos", p["revisar"])
        out += [f"- No se tocan: {', '.join(NUNCA)}"]
        nov = _nucleo.novedades(fuente, v_local)
        if nov and v_nueva != v_local:
            lineas = nov.splitlines()
            out += ["", "## Novedades", "", *lineas[:60]]
            if len(lineas) > 60:
                out += ["", f"(… {len(lineas) - 60} líneas más en CHANGELOG.md)"]
        cambios = p["agregar"] or p["reemplazar"] or p["eliminar"]

        if not a.aplicar:
            sufijo = (f"--desde {origen} " if a.desde else "") + "--aplicar"
            out += ["", "Vista previa: nada cambió." + (f" Para aplicar: python .fabrica/scripts/actualizar_nucleo.py {sufijo}"
                                                        if cambios else " El núcleo ya está al día.")]
            print("\n".join(out))
            return 0
        print("\n".join(out))

        if not cambios:
            print("\nEl núcleo ya está al día.")
            _nucleo.escribir_manifiesto(RAIZ, p["nuevos"])
            registrar_version(v_nueva)
            if repo and not a.sin_commit:
                git("add", "--", _nucleo.MANIFIESTO.as_posix(), *([".fabrica/config.json"] if CONFIG.exists() else []))
                rc_c, _ = git("commit", "-q", "-m", f"Registra el núcleo instalado ({v_nueva or 'sin versión'})")
                if rc_c == 0:
                    print("Commit: registro del núcleo instalado.")
            return 0

        local, nueva = _nucleo.ruta_larga(RAIZ), _nucleo.ruta_larga(fuente)
        respaldo = local / ".fabrica" / "respaldo-nucleo" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
        for rel in p["reemplazar"] + p["eliminar"] + [_nucleo.MANIFIESTO.as_posix(), ".fabrica/config.json"]:
            src = local / rel
            if src.exists():
                (respaldo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, respaldo / rel)

        def revertir():
            for rel in p["agregar"]:
                (local / rel).unlink(missing_ok=True)
            for x in respaldo.rglob("*"):
                if x.is_file():
                    destino = local / x.relative_to(respaldo)
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(x, destino)

        for rel in p["agregar"] + p["reemplazar"]:
            (local / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(nueva / rel, local / rel)
        for rel in p["eliminar"]:
            (local / rel).unlink(missing_ok=True)
            carpeta = (local / rel).parent
            while carpeta != local and carpeta.exists() and not any(carpeta.iterdir()):
                carpeta.rmdir()
                carpeta = carpeta.parent
        # El registro guarda solo lo que vino del núcleo; lo propio de la instancia nunca entra, o se borraría después
        _nucleo.escribir_manifiesto(RAIZ, p["nuevos"])
        registrar_version(v_nueva)
        print(f"\nAplicado. Respaldo de lo reemplazado: {respaldo.relative_to(local).as_posix()}/")

        print("Verificando la fábrica con el núcleo nuevo...")
        r = subprocess.run([sys.executable, ".fabrica/scripts/verificar.py"], cwd=RAIZ, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        salida = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode != 0:
            revertir()
            print("La verificación falló con el núcleo nuevo: se revirtió la actualización. Nada cambió.\n"
                  + "\n".join(salida.splitlines()[-15:])
                  + "\nAvísale a quien mantiene el núcleo.")
            return 1
        print((salida.splitlines() or ["Verificación: sin salida"])[-1])

        if repo and not a.sin_commit:
            rutas_git = [e.rstrip("/") for e in p["union"]] + [_nucleo.MANIFIESTO.as_posix()]
            if CONFIG.exists():
                rutas_git.append(".fabrica/config.json")
            existentes = [x for x in rutas_git if (RAIZ / x).exists() or any(e.startswith(x) for e in p["eliminar"])]
            git("add", "-A", "--", *existentes)
            rc_c, salida_c = git("commit", "-q", "-m", f"Actualiza el núcleo a {v_nueva or 'la versión nueva'}")
            print(f"Commit: «Actualiza el núcleo a {v_nueva}»." if rc_c == 0 else f"No se hizo el commit: {salida_c[:400]}")
            if rc_c == 0:
                print("Para deshacer la actualización completa: git revert HEAD")
        if p["modificados"]:
            print("Revisa los archivos del núcleo que estaban modificados a mano: su versión anterior quedó en el respaldo. "
                  "Si eran ajustes propios, llévalos a instancia/ (nucleo/actualizaciones.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
