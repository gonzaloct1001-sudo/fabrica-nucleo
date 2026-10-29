"""Lógica común para actualizar una zona administrada sin tocar lo propio: el núcleo en una instancia, o el kit en un
proyecto.

Una actualización compara archivo por archivo, usando la huella de cada uno:
- qué es nuevo, qué cambió y qué ya no viene;
- qué se modificó a mano y qué es propio.

Antes de reemplazar o eliminar algo, lo respalda. Después corre el verificador y, si falla, revierte todo. Si
termina bien, deja un solo commit.
"""
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Tuple

import _nucleo


@dataclass
class Destino:
    raiz: Path                       # carpeta que se actualiza
    nunca: Tuple[str, ...]           # rutas que una actualización jamás toca
    version_local: str
    registrar_version: Callable[[str], None]
    verificador: List[str]           # comando que debe pasar con la versión nueva
    mensaje_commit: Callable[[str], str]
    comando_aplicar: str             # cómo se aplica, para la vista previa
    respaldar_tambien: List[str] = field(default_factory=list)  # archivos propios que cambian al registrar la versión
    consejo_modificados: str = "Si eran ajustes propios, llévalos fuera de la zona administrada."


def git(raiz, *args):
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def es_repositorio(raiz):
    rc, top = git(raiz, "rev-parse", "--show-toplevel")
    return rc == 0 and Path(top).resolve() == Path(raiz).resolve()


def exigir_arbol_limpio(raiz):
    """Termina con un mensaje si hay cambios sin commit: la actualización debe quedar en un commit propio."""
    if es_repositorio(raiz):
        rc, sucio = git(raiz, "status", "--porcelain")
        if rc == 0 and sucio:
            sys.exit("Hay cambios sin commit. Haz commit o guárdalos aparte antes de actualizar, para que la "
                     "actualización quede en un commit propio y se pueda revertir.\n" + sucio[:800])


def plan(raiz, fuente, nunca):
    entradas_nuevas = _nucleo.rutas(fuente)
    entradas_locales = _nucleo.rutas(raiz) if (Path(raiz) / "NUCLEO.txt").exists() else []
    union = list(dict.fromkeys(entradas_locales + entradas_nuevas))
    union = [e for e in union if not any(e.startswith(n) for n in nunca)]
    nuevos = _nucleo.archivos(fuente, [e for e in entradas_nuevas if e in union])
    locales = _nucleo.archivos(raiz, union)
    manifiesto = _nucleo.leer_manifiesto(raiz)
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


def ejecutar(d: Destino, fuente, origen, version_nueva, novedades, aplicar, sin_commit, titulo="Actualización"):
    """Muestra la vista previa o aplica la actualización de `fuente` sobre `d.raiz`. Devuelve el código de salida."""
    raiz = Path(d.raiz)
    repo = es_repositorio(raiz)
    p = plan(raiz, fuente, d.nunca)
    out = [f"# {titulo}", "", f"- Origen: {origen}", f"- Versión: {d.version_local or '?'} → {version_nueva or '?'}",
           f"- Archivos: {len(p['agregar'])} nuevos · {len(p['reemplazar'])} cambiados · "
           f"{len(p['eliminar'])} eliminados · {p['iguales']} iguales"]
    out += lista("Nuevos", p["agregar"]) + lista("Cambiados", p["reemplazar"])
    out += lista("Eliminados (la versión nueva ya no los trae)", p["eliminar"])
    out += lista("Modificados a mano (se respaldan antes de reemplazarlos)", p["modificados"])
    out += lista("Propios dentro de carpetas administradas (se conservan)", p["propios"])
    out += lista("Sin registro de lo instalado: no se borran, revísalos", p["revisar"])
    out += [f"- No se tocan: {', '.join(d.nunca)}"]
    if novedades and version_nueva != d.version_local:
        lineas = novedades.splitlines()
        out += ["", "## Novedades", "", *lineas[:60]]
        if len(lineas) > 60:
            out += ["", f"(… {len(lineas) - 60} líneas más en CHANGELOG.md)"]
    cambios = p["agregar"] or p["reemplazar"] or p["eliminar"]

    if not aplicar:
        out += ["", "Vista previa: nada cambió." + (f" Para aplicar: {d.comando_aplicar}" if cambios
                                                    else " Ya está al día.")]
        print("\n".join(out))
        return 0
    print("\n".join(out))

    if not cambios:
        print("\nYa está al día.")
        _nucleo.escribir_manifiesto(raiz, p["nuevos"])
        d.registrar_version(version_nueva)
        if repo and not sin_commit:
            git(raiz, "add", "--", _nucleo.MANIFIESTO.as_posix(), *[r for r in d.respaldar_tambien if (raiz / r).exists()])
            rc_c, _ = git(raiz, "commit", "-q", "-m", f"Registra lo instalado ({version_nueva or 'sin versión'})")
            if rc_c == 0:
                print("Commit: registro de lo instalado.")
        return 0

    local, nueva = _nucleo.ruta_larga(raiz), _nucleo.ruta_larga(fuente)
    # Una carpeta de respaldo propia por actualización: si dos caen en el mismo segundo y compartieran carpeta, revertir
    # la segunda restauraría también los respaldos de la primera
    sello = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    respaldo, n = local / ".fabrica" / "respaldo-nucleo" / sello, 1
    while respaldo.exists():
        n += 1
        respaldo = local / ".fabrica" / "respaldo-nucleo" / f"{sello}_{n}"
    for rel in p["reemplazar"] + p["eliminar"] + [_nucleo.MANIFIESTO.as_posix(), *d.respaldar_tambien]:
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
    # El registro guarda solo lo que vino de la fuente; lo propio nunca entra, o se borraría en la próxima
    _nucleo.escribir_manifiesto(raiz, p["nuevos"])
    d.registrar_version(version_nueva)
    print(f"\nAplicado. Respaldo de lo reemplazado: {respaldo.relative_to(local).as_posix()}/")

    print("Verificando con la versión nueva...")
    r = subprocess.run(d.verificador, cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600)
    salida = ((r.stdout or "") + (r.stderr or "")).strip()
    if r.returncode != 0:
        revertir()
        print("La verificación falló con la versión nueva: se revirtió la actualización. Nada cambió.\n"
              + "\n".join(salida.splitlines()[-15:]) + "\nAvísale a quien mantiene el núcleo.")
        return 1
    print((salida.splitlines() or ["Verificación: sin salida"])[-1])

    if repo and not sin_commit:
        rutas_git = [e.rstrip("/") for e in p["union"]] + [_nucleo.MANIFIESTO.as_posix(), *d.respaldar_tambien]
        existentes = [x for x in rutas_git if (raiz / x).exists() or any(e.startswith(x) for e in p["eliminar"])]
        git(raiz, "add", "-A", "--", *existentes)
        mensaje = d.mensaje_commit(version_nueva)
        rc_c, salida_c = git(raiz, "commit", "-q", "-m", mensaje)
        print(f"Commit: «{mensaje}»." if rc_c == 0 else f"No se hizo el commit: {salida_c[:400]}")
        if rc_c == 0:
            print("Para deshacer la actualización completa: git revert HEAD")
    if p["modificados"]:
        print(f"Revisa los archivos modificados a mano: su versión anterior quedó en el respaldo. {d.consejo_modificados}")
    return 0
