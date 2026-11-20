#!/usr/bin/env python3
"""Ensaya la actualización del kit de un proyecto en una copia temporal, sin tocar el original (núcleo 0.13.2).

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL del proyecto>
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL> --informe ensayo.md
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL> --sin-prs
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL> --pr 216 --pr 232    solo esos PR

Conviene darle la URL de GitHub: así ensaya sobre la rama principal del día y trae los PR abiertos. Con una carpeta,
ensaya sobre su rama principal (`--rama` para otra) y trae los PR de su remoto `origin`.

Hace, en una carpeta temporal que borra al terminar:
1. Clona el proyecto (su rama principal).
2. Aplica la actualización con `actualizar_kit.py`, que verifica y revierte si falla. Si encuentra «patas» (archivos
   del kit editados a mano), se detiene ahí y lo informa: el original sigue igual.
3. Corre la verificación como la correría la CI en el PR de la actualización, con y sin la etiqueta nucleo-aprobado.
4. Comprueba que fuera de la zona del kit solo cambien los archivos que la actualización administra (la versión en
   proyecto.json, los hooks en .claude/settings.json y los flujos que ajustó para ignorar wip/).
5. Con GitHub a mano, prueba encima cada PR abierto, como si se integrara después: si se une sin conflictos y si pasa
   la verificación. Lo compara con el master sin actualizar, para separar lo que ya fallaba de lo que causaría la
   actualización.
6. Deja un informe en Markdown.

No sube nada, no abre PRs y no cambia el original. Usa la biblioteca estándar, `git` y, si está, `gh api` (solo REST).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FUERA_ADMINISTRADOS = (".fabrica/proyecto.json", ".claude/settings.json", ".fabrica/nucleo-instalado.csv")
ZONAS_DELICADAS = (".fabrica/scripts/", ".fabrica/nucleo/", ".github/workflows/fabrica")
TIEMPO = 900


def correr(orden, cwd, tope=TIEMPO):
    try:
        hecho = subprocess.run(orden, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=tope,
                               check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return hecho.returncode, ((hecho.stdout or "") + (hecho.stderr or "")).strip()


def git(cwd, *args):
    return correr(["git", *args], cwd)


def repositorio_en_github(url):
    """«dueño/repo» de una URL o ruta remota de GitHub, o cadena vacía."""
    m = re.search(r"github\.com[:/]+([^/]+)/([^/\s]+?)(?:\.git)?/?$", url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def gh(*args):
    if not shutil.which("gh"):
        return None
    rc, salida = correr(["gh", "api", *args], RAIZ, tope=60)
    if rc != 0:
        return None
    try:
        return json.loads(salida)
    except ValueError:
        return None


def ultimas(texto, n=12):
    return "\n".join(texto.splitlines()[-n:])


def verificar(copia, base=None, etiquetas=None):
    orden = [sys.executable, ".fabrica/scripts/verificar_proyecto.py"]
    if base:
        orden += ["--base", base, "--etiquetas", ",".join(etiquetas or [])]
    rc, salida = correr(orden, copia)
    errores = [l[2:] for l in salida.splitlines() if l.startswith("- ")]
    return rc == 0, errores, salida


def probar_pr(copia, base, numero, etiquetas):
    """(se une, errores) del PR `numero` encima de `base` en la copia. Un conflicto cuenta como un error."""
    git(copia, "checkout", "-q", "-B", f"ensayo-pr-{numero}", base)
    rc, salida = git(copia, "merge", "-q", "--no-edit", f"pr-{numero}")
    if rc != 0:
        rc_c, choques = git(copia, "diff", "--name-only", "--diff-filter=U")
        git(copia, "merge", "--abort")
        return False, ["conflicto en " + ", ".join(choques.splitlines()[:5])]
    _, errores, _ = verificar(copia, base, etiquetas)
    return True, errores


def veredicto(sin, con):
    """Qué le hace la actualización a un PR, comparando sus errores sin ella (`sin`) y con ella (`con`).

    Cada uno es (se une, errores). La actualización lo afecta si con ella aparece un error que antes no estaba, aunque
    el PR ya fallara por otra cosa.
    """
    nuevos = [e for e in con[1] if e not in sin[1]]
    if not con[1]:
        return "bien"
    if nuevos:
        return "**la actualización lo afecta:** " + "; ".join(e[:180] for e in nuevos[:3])
    return "ya fallaba igual sin la actualización: " + "; ".join(e[:180] for e in con[1][:2])


def main(argumentos=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("proyecto", help="carpeta del proyecto o URL de su repositorio")
    analizador.add_argument("--informe", help="además, guardar el informe en este archivo")
    analizador.add_argument("--sin-prs", action="store_true", help="no probar los PR abiertos")
    analizador.add_argument("--pr", type=int, action="append", help="probar solo este PR (se puede repetir)")
    analizador.add_argument("--rama", help="con una carpeta, la rama que se ensaya (por defecto, su principal)")
    analizador.add_argument("--reemplazar-editados", action="store_true",
                            help="ensayar como si se decidiera reemplazar las patas, para ver el resto del ensayo")
    opciones = analizador.parse_args(argumentos)

    origen = opciones.proyecto
    if Path(origen).exists():
        origen = str(Path(origen).resolve())
    informe = [f"# Ensayo de la actualización · {Path(origen.rstrip('/')).name}", ""]
    with tempfile.TemporaryDirectory(prefix="fabrica-ensayo-") as tmp:
        copia = Path(tmp) / "proyecto"
        rc, salida = git(tmp, "clone", "-q", "--no-hardlinks", origen, str(copia))
        if rc != 0:
            print(f"No se pudo clonar {origen}: {ultimas(salida, 4)}")
            return 1
        if opciones.rama or Path(origen).exists():
            rama = opciones.rama or principal_de(Path(origen))
            if rama and git(copia, "checkout", "-q", rama)[0] != 0:
                print(f"No existe la rama {rama} en {origen}.")
                return 1
        git(copia, "config", "user.email", "ensayo@fabrica.local")
        git(copia, "config", "user.name", "Ensayo de la fábrica")
        _, principal = git(copia, "rev-parse", "--abbrev-ref", "HEAD")
        _, antes = git(copia, "rev-parse", "--short", "HEAD")
        git(copia, "branch", "-q", "sin-actualizar", "HEAD")
        remoto = origen
        if Path(origen).exists():
            rc_r, url = git(Path(origen), "remote", "get-url", "origin")
            remoto = url if rc_r == 0 and url else origen
        repo = repositorio_en_github(remoto)
        informe += [f"- **Copia de:** {repo or origen}, rama `{principal}` en `{antes}`.",
                    "- **El original no se tocó:** todo pasó en una carpeta temporal, ya borrada."]

        actualizar = [sys.executable, str(RAIZ / ".fabrica/scripts/actualizar_kit.py"), str(copia), "--aplicar"]
        if opciones.reemplazar_editados:
            actualizar.append("--reemplazar-editados")
            informe.append("- **Ensayado con `--reemplazar-editados`:** las patas se reemplazan en la copia, para ver el "
                           "resto. En el original, primero se decide qué hacer con cada una.")
        rc, salida = correr(actualizar, RAIZ)
        version = re.search(r"Versión: (.+)", salida)
        informe += ["", "## La actualización", "", f"- **Versión:** {version.group(1) if version else '?'}"]
        resumen = re.search(r"- Archivos: (.+)", salida)
        if resumen:
            informe.append(f"- **Archivos del kit:** {resumen.group(1)}")
        for titulo, etiqueta in (("Editados a mano dentro de la zona administrada", "Archivos del kit editados a mano"),
                                 ("Propios con el mismo nombre que uno", "Propios que chocan con el kit (se conservan)"),
                                 ("Propios dentro de carpetas administradas", "Propios dentro de la zona (se conservan)")):
            bloque = re.search(rf"^- {re.escape(titulo)}[^:\n]*: (\d+)\n((?:  - .+\n?)+)", salida, re.M)
            if bloque:
                informe.append(f"- **{etiqueta}:** {bloque.group(1)}")
                informe += [f"  {l.strip()}" for l in bloque.group(2).splitlines()[:10]]
        chocan = re.search(r"^- Propios con el mismo nombre que uno[^\n]*\n((?:  - .+\n?)+)", salida, re.M)
        delicados = [l.strip()[2:] for l in (chocan.group(1).splitlines() if chocan else [])
                     if l.strip()[2:].startswith(ZONAS_DELICADAS)]
        if delicados:
            informe.append("- **Alarma:** chocan archivos de las herramientas o del método de la fábrica ("
                           + ", ".join(delicados[:5]) + "). Quedaría una mezcla de versiones: revisa el registro de lo "
                           "instalado antes de actualizar.")
        if rc != 0:
            motivo = "se detuvo por archivos del kit editados o borrados a mano" if "se detuvo" in salida else "falló"
            informe += ["", f"**Resultado: la actualización {motivo}. Nada cambió.**", "", "```",
                        ultimas(salida, 15), "```"]
            return terminar(informe, opciones.informe, 1)
        verificada = re.search(r"Verificación del proyecto: .+", salida)
        informe.append("- **Aplicada en la copia.** " + (verificada.group(0) if verificada else "Sin línea de verificación."))
        informe += [f"- {l.strip()}" for l in salida.splitlines() if l.startswith(("Rutas propias", "Flujo ajustado",
                                                                                     "Se conservaron", "Aviso:"))]

        ajustados = re.findall(r"^Flujo ajustado para ignorar las ramas wip/: (.+)$", salida, re.M)
        _, cambiados = git(copia, "-c", "core.quotepath=off", "diff", "--no-renames", "--name-only", "sin-actualizar",
                           "HEAD")
        zona = [l.strip() for l in (copia / "NUCLEO.txt").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        fuera = [c for c in cambiados.splitlines() if c and not any(c == e or (e.endswith("/") and c.startswith(e))
                                                                    for e in zona)]
        inesperados = [c for c in fuera if c not in FUERA_ADMINISTRADOS and c not in ajustados]
        informe += ["", "## Fuera de la zona del kit", "",
                    f"- Cambian {len(fuera)} archivo(s), todos administrados por la actualización: "
                    + (", ".join(f"`{c}`" for c in fuera) or "ninguno") if not inesperados else
                    f"- **Cambian archivos que no debería tocar:** {', '.join(inesperados)}"]

        pasa_sin, errores_sin, _ = verificar(copia, "sin-actualizar")
        pasa_con, errores_con, _ = verificar(copia, "sin-actualizar", ["nucleo-aprobado"])
        informe += ["", "## La CI del PR de la actualización (simulada)", "",
                    f"- Sin etiquetas: {'pasa' if pasa_sin else 'en rojo'}"
                    + (f" ({errores_sin[0][:160]})" if errores_sin else ""),
                    f"- Con `nucleo-aprobado`: {'pasa' if pasa_con else 'en rojo'}"
                    + (f" ({errores_con[0][:160]})" if errores_con else "")]

        rc_d, despues = correr([sys.executable, ".fabrica/scripts/inventario.py", "--json"], copia)
        if rc_d == 0:
            try:
                d = json.loads(despues)
                informe += ["", "## Inventario después", "",
                            f"- Kit: {d['kit']['instalados']} archivos, {d['kit']['intactos']} intactos.",
                            f"- Propio dentro de la zona: {len(d['propio_en_la_zona']['con_local'])} con local-, "
                            f"{len(d['propio_en_la_zona']['sin_prefijo'])} sin prefijo.",
                            f"- Posibles duplicados del kit: {len(d['posibles_duplicados'])}"
                            + "".join(f"\n  - `{x['propio']}` ↔ `{x['kit']}`" for x in d["posibles_duplicados"])]
            except (ValueError, KeyError):
                pass

        if opciones.pr:
            prs = [{"number": n} for n in opciones.pr]
            if repo:
                prs = [gh(f"repos/{repo}/pulls/{n}") or {"number": n} for n in opciones.pr]
        else:
            prs = [] if opciones.sin_prs or not repo else (gh(f"repos/{repo}/pulls?state=open&per_page=50") or [])
        if not opciones.sin_prs:
            informe += ["", "## PR abiertos, encima de la actualización", ""]
            if not repo and not opciones.pr:
                informe.append("- No se probaron: el proyecto no está en GitHub o no se reconoció su dirección.")
            elif not prs:
                informe.append("- No hay PR abiertos, o GitHub no respondió.")
        _, actualizado = git(copia, "rev-parse", "HEAD")
        for pr in prs:
            numero = pr.get("number")
            if not isinstance(numero, int):
                continue
            rc, salida = git(copia, "fetch", "-q", remoto, f"refs/pull/{numero}/head:pr-{numero}")
            if rc != 0:
                informe.append(f"- #{numero}: no se pudo traer ({ultimas(salida, 1)[:120]})")
                continue
            etiquetas = [e.get("name", "") for e in pr.get("labels", [])]
            con = probar_pr(copia, actualizado, numero, etiquetas)
            sin = probar_pr(copia, "sin-actualizar", numero, etiquetas)
            rama_pr = (pr.get("head") or {}).get("ref", "")
            titulo = f" ({pr.get('title', '')[:60]})" if pr.get("title") else ""
            informe.append(f"- #{numero}" + (f" `{rama_pr}`" if rama_pr else "") + f"{titulo}: {veredicto(sin, con)}")
        return terminar(informe, opciones.informe, 0)


def principal_de(carpeta):
    """La rama principal de un repositorio local: la de su origin, o main/master si existe."""
    rc, ref = git(carpeta, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if rc == 0 and ref.startswith("origin/"):
        return ref[len("origin/"):]
    for rama in ("main", "master"):
        if git(carpeta, "rev-parse", "--verify", "--quiet", f"refs/heads/{rama}")[0] == 0:
            return rama
    return ""


def terminar(informe, archivo, codigo):
    texto = "\n".join(informe) + "\n"
    print(texto)
    if archivo:
        Path(archivo).write_text(texto, encoding="utf-8")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
