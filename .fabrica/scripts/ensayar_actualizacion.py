#!/usr/bin/env python3
"""Ensaya la actualización del kit de un proyecto en una copia temporal, sin tocar el original (núcleo 0.13.2).

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL del proyecto>
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL> --informe ensayo.md
    python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL> --sin-prs

Hace, en una carpeta temporal que borra al terminar:
1. Clona el proyecto (su rama principal).
2. Aplica la actualización con `actualizar_kit.py`, que verifica y revierte si falla. Si encuentra «patas» (archivos
   del kit editados a mano), se detiene ahí y lo informa: el original sigue igual.
3. Corre la verificación como la correría la CI en el PR de la actualización, con y sin la etiqueta nucleo-aprobado.
4. Comprueba que fuera de la zona del kit solo cambien los archivos que la actualización administra (la versión en
   proyecto.json, los hooks en .claude/settings.json y el filtro wip/ de los flujos).
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
FUERA_ADMINISTRADOS = (".fabrica/proyecto.json", ".claude/settings.json", ".gitignore")
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
    """(se une, pasa, detalle) del PR `numero` encima de `base` en la copia."""
    git(copia, "checkout", "-q", "-B", f"ensayo-pr-{numero}-{base}", base)
    rc, salida = git(copia, "merge", "-q", "--no-edit", f"pr-{numero}")
    if rc != 0:
        rc_c, choques = git(copia, "diff", "--name-only", "--diff-filter=U")
        git(copia, "merge", "--abort")
        return False, False, "conflicto en " + ", ".join(choques.splitlines()[:5])
    pasa, errores, _ = verificar(copia, base, etiquetas)
    return True, pasa, "; ".join(e[:180] for e in errores[:3])


def main(argumentos=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("proyecto", help="carpeta del proyecto o URL de su repositorio")
    analizador.add_argument("--informe", help="además, guardar el informe en este archivo")
    analizador.add_argument("--sin-prs", action="store_true", help="no probar los PR abiertos")
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
        git(copia, "config", "user.email", "ensayo@fabrica.local")
        git(copia, "config", "user.name", "Ensayo de la fábrica")
        _, principal = git(copia, "rev-parse", "--abbrev-ref", "HEAD")
        _, antes = git(copia, "rev-parse", "--short", "HEAD")
        git(copia, "branch", "-q", "sin-actualizar", "HEAD")
        remoto = origen if not Path(origen).exists() else git(Path(origen), "remote", "get-url", "origin")[1]
        repo = repositorio_en_github(remoto)
        informe += [f"- **Copia de:** {repo or origen}, rama `{principal}` en `{antes}`.",
                    "- **El original no se tocó:** todo pasó en una carpeta temporal, ya borrada."]

        actualizar = [sys.executable, str(RAIZ / ".fabrica/scripts/actualizar_kit.py"), str(copia), "--aplicar"]
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
        if rc != 0:
            motivo = "se detuvo por archivos del kit editados a mano" if "se detuvo" in salida else "falló"
            informe += ["", f"**Resultado: la actualización {motivo}. Nada cambió.**", "", "```",
                        ultimas(salida, 15), "```"]
            return terminar(informe, opciones.informe, 1)
        verificada = re.search(r"Verificación del proyecto: .+", salida)
        informe.append("- **Aplicada en la copia.** " + (verificada.group(0) if verificada else "Sin línea de verificación."))
        informe += [f"- {l.strip()}" for l in salida.splitlines() if l.startswith(("Rutas propias", "Flujo ajustado",
                                                                                     "Se conservaron", "Aviso:"))]

        _, cambiados = git(copia, "diff", "--name-only", "sin-actualizar", "HEAD")
        zona = [l.strip() for l in (copia / "NUCLEO.txt").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        fuera = [c for c in cambiados.splitlines() if c and not any(c == e or (e.endswith("/") and c.startswith(e))
                                                                    for e in zona)]
        inesperados = [c for c in fuera if c not in FUERA_ADMINISTRADOS and not c.startswith((".github/workflows/",
                                                                                           ".fabrica/nucleo-instalado"))]
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

        prs = [] if opciones.sin_prs or not repo else (gh(f"repos/{repo}/pulls?state=open&per_page=50") or [])
        if not opciones.sin_prs:
            informe += ["", "## PR abiertos, encima de la actualización", ""]
            if not repo:
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
            se_une, pasa, detalle = probar_pr(copia, actualizado, numero, etiquetas)
            se_une_0, pasa_0, _ = probar_pr(copia, "sin-actualizar", numero, etiquetas)
            if se_une and pasa:
                veredicto = "bien"
            elif (se_une, pasa) == (se_une_0, pasa_0):
                veredicto = "igual que sin la actualización (ya fallaba): " + detalle
            else:
                veredicto = "**la actualización lo afecta:** " + detalle
            informe.append(f"- #{numero} `{pr.get('head', {}).get('ref', '')}` ({pr.get('title', '')[:60]}): {veredicto}")
        return terminar(informe, opciones.informe, 0)


def terminar(informe, archivo, codigo):
    texto = "\n".join(informe) + "\n"
    print(texto)
    if archivo:
        Path(archivo).write_text(texto, encoding="utf-8")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
