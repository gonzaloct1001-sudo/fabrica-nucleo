#!/usr/bin/env python3
"""Inventario de activos de un proyecto de la fábrica, o de una instancia (núcleo 0.13.2).

Uso, desde la raíz del proyecto (o de la instancia, con --raiz):
    python .fabrica/scripts/inventario.py                 informe en Markdown
    python .fabrica/scripts/inventario.py --json          lo mismo, para otras herramientas
    python kit/.fabrica/scripts/inventario.py --raiz .    en una instancia

Se calcula del disco y del registro de lo instalado (`.fabrica/nucleo-instalado.csv`); nunca se escribe a mano.
Dice:
- **Kit o núcleo:** la versión, cuántos archivos instaló y si siguen intactos: editados a mano («patas») y faltantes.
- **Propio dentro de la zona:** lo que tiene el prefijo local- y lo que no (se conserva, pero conviene renombrarlo).
- **Posibles duplicados:** una pieza propia que parece hacer lo mismo que una del kit (por ejemplo,
  `local-construir-en-sesion` y `construir-en-sesion`, o `scripts/estado.py` y `.fabrica/scripts/estado.py`).
- **Creado por el proyecto:** sus agentes, skills y comandos propios: candidatos a revisar al recoger aprendizajes.

Solo lee. Usa la biblioteca estándar y, si está, `git` (para listar solo lo registrado).
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFIESTO = ".fabrica/nucleo-instalado.csv"
PIEZAS = (".claude/agents/", ".claude/skills/", ".claude/commands/", ".github/workflows/")
IGNORAR = re.compile(r"(^|/)(__pycache__|\.git|node_modules)/|\.pyc$")


def huella(ruta):
    """La misma huella que la actualización: sha256 del contenido, sin la diferencia CRLF/LF en los de texto."""
    datos = Path(ruta).read_bytes()
    if b"\0" not in datos[:8192]:
        datos = datos.replace(b"\r\n", b"\n")
    return hashlib.sha256(datos).hexdigest()[:20]


def zona(raiz):
    lista = raiz / "NUCLEO.txt"
    if not lista.is_file():
        return ()
    return tuple(l.strip() for l in lista.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.lstrip().startswith("#"))


def en_zona(rel, entradas):
    return any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in entradas)


def archivos(raiz):
    """Los archivos del repositorio: los registrados en git o, sin git, los del disco."""
    hecho = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z"], capture_output=True, check=False)
    if hecho.returncode == 0:
        lista = [x for x in hecho.stdout.decode("utf-8", "replace").split("\0") if x]
    else:
        lista = [p.relative_to(raiz).as_posix() for p in raiz.rglob("*") if p.is_file()]
    return sorted(x for x in lista if not IGNORAR.search(x))


def leer_manifiesto(raiz):
    ruta = raiz / MANIFIESTO
    if not ruta.is_file():
        return None
    with open(ruta, encoding="utf-8", newline="") as f:
        return {fila["ruta"]: fila["huella"] for fila in csv.DictReader(f) if fila.get("ruta")}


def version(raiz):
    for rel, clave in ((".fabrica/proyecto.json", "nucleo"), (".fabrica/config.json", "nucleo_version")):
        try:
            return json.loads((raiz / rel).read_text(encoding="utf-8")).get(clave, "") or ""
        except (OSError, ValueError):
            continue
    return ""


def pieza(rel):
    """(tipo, nombre) de un agente, skill, comando o flujo; o None."""
    for prefijo in PIEZAS:
        if rel.startswith(prefijo):
            resto = rel[len(prefijo):]
            nombre = resto.split("/", 1)[0] if prefijo == ".claude/skills/" else Path(resto).stem
            return prefijo.strip("/").rsplit("/", 1)[-1], nombre
    return None


def sin_local(nombre):
    return nombre[len("local-"):] if nombre.startswith("local-") else nombre


def inventario(raiz):
    raiz = Path(raiz).resolve()
    entradas = zona(raiz)
    instalado = leer_manifiesto(raiz)
    todos = archivos(raiz)
    kit = instalado or {}
    editados = sorted(r for r, h in kit.items() if (raiz / r).is_file() and huella(raiz / r) != h)
    faltan = sorted(r for r in kit if not (raiz / r).exists())
    propios_zona = [r for r in todos if en_zona(r, entradas) and r not in kit and r != MANIFIESTO]
    con_local = sorted(r for r in propios_zona if any(p.startswith("local-") for p in r.split("/")))
    sin_prefijo = sorted(r for r in propios_zona if r not in con_local)

    piezas_kit = {}
    for r in kit:
        p = pieza(r)
        if p:
            piezas_kit.setdefault(p, r)
    nombres_kit = {(tipo, nombre) for tipo, nombre in piezas_kit}
    creadas, duplicados = {}, []
    for r in propios_zona:
        p = pieza(r)
        if not p:
            continue
        tipo, nombre = p
        if (tipo, nombre) in creadas:
            continue
        creadas[(tipo, nombre)] = r
        base = sin_local(nombre)
        if base != nombre and (tipo, base) in nombres_kit:
            duplicados.append({"propio": r, "kit": piezas_kit[(tipo, base)], "motivo": "mismo nombre sin local-"})
    scripts_kit = {Path(r).name: r for r in kit if r.startswith(".fabrica/scripts/") and r.endswith(".py")}
    for r in todos:
        if en_zona(r, entradas) or not r.endswith(".py") or Path(r).name.startswith(("test_", "_")):
            continue
        if Path(r).name in scripts_kit and "/" in r and r.split("/", 1)[0] in ("scripts", "herramientas", "tools"):
            duplicados.append({"propio": r, "kit": scripts_kit[Path(r).name], "motivo": "script con el mismo nombre"})

    return {
        "raiz": raiz.name,
        "version": version(raiz),
        "registro": instalado is not None,
        "kit": {"instalados": len(kit), "intactos": len(kit) - len(editados) - len(faltan), "editados": editados,
                "faltan": faltan},
        "propio_en_la_zona": {"con_local": con_local, "sin_prefijo": sin_prefijo},
        "posibles_duplicados": duplicados,
        "creado_por_el_proyecto": [{"tipo": t, "nombre": n, "ruta": r} for (t, n), r in sorted(creadas.items())],
        "fuera_de_la_zona": len([r for r in todos if not en_zona(r, entradas)]),
    }


def markdown(datos):
    k = datos["kit"]
    salida = [f"# Inventario · {datos['raiz']}", "",
              f"- **Versión instalada:** {datos['version'] or 'sin registrar'}"]
    if not datos["registro"]:
        salida.append(f"- **Sin registro de lo instalado** ({MANIFIESTO}): no se puede saber si el kit está intacto. "
                      "Lo crea la próxima actualización.")
    else:
        estado = "intacto" if not (k["editados"] or k["faltan"]) else "con diferencias"
        salida.append(f"- **Kit:** {k['instalados']} archivos instalados, {k['intactos']} intactos ({estado}).")
        for titulo, lista in (("Editados a mano («patas»)", k["editados"]), ("Faltan", k["faltan"])):
            if lista:
                salida.append(f"  - {titulo}: {len(lista)}")
                salida += [f"    - `{r}`" for r in lista[:20]]
    z = datos["propio_en_la_zona"]
    salida.append(f"- **Propio dentro de la zona del kit:** {len(z['con_local'])} con `local-` y "
                  f"{len(z['sin_prefijo'])} sin el prefijo.")
    if z["sin_prefijo"]:
        salida.append("  - Sin prefijo (se conservan al actualizar; conviene renombrarlos a `local-*`):")
        salida += [f"    - `{r}`" for r in z["sin_prefijo"][:20]]
    if datos["posibles_duplicados"]:
        salida.append("- **Posibles duplicados del kit** (decidir cuál queda):")
        salida += [f"  - `{d['propio']}` ↔ `{d['kit']}` ({d['motivo']})" for d in datos["posibles_duplicados"]]
    if datos["creado_por_el_proyecto"]:
        salida.append("- **Creado por el proyecto** (candidatos a revisar al recoger aprendizajes):")
        salida += [f"  - {c['tipo']}: `{c['nombre']}`" for c in datos["creado_por_el_proyecto"]]
    salida.append(f"- **Fuera de la zona del kit:** {datos['fuera_de_la_zona']} archivos del proyecto (la actualización "
                  "nunca los toca).")
    return "\n".join(salida)


def main(argumentos=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analizador = argparse.ArgumentParser(description="Inventario de activos del proyecto o de la instancia.")
    analizador.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]),
                            help="carpeta del proyecto o de la instancia (por defecto, la de este script)")
    analizador.add_argument("--json", action="store_true", help="salida en JSON")
    opciones = analizador.parse_args(argumentos)
    datos = inventario(opciones.raiz)
    print(json.dumps(datos, ensure_ascii=False, indent=2) if opciones.json else markdown(datos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
